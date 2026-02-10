"""Tests for the main API endpoints"""

import pytest
from fastapi import status


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_chess_club_details(self, client):
        """Test specific details of Chess Club"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert chess_club["description"] == "Learn strategies and compete in chess tournaments"
        assert chess_club["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
        assert chess_club["max_participants"] == 12
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_successful_signup(self, client):
        """Test successful student signup"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "new_student@mergington.edu"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Signed up new_student@mergington.edu for Chess Club"
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "new_student@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_for_multiple_activities(self, client):
        """Test student can signup for multiple activities"""
        email = "multi_activity@mergington.edu"
        
        # Signup for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Signup for Programming Class
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify student is in both
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Dance Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Activity not found"
    
    def test_duplicate_signup(self, client):
        """Test that duplicate signup returns 400"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Student already signed up for this activity"
    
    def test_signup_preserves_other_participants(self, client):
        """Test that signing up doesn't affect other participants"""
        # Get initial participants
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()["Chess Club"]["participants"].copy()
        
        # Add new student
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "new@mergington.edu"}
        )
        
        # Verify original participants still there
        final_response = client.get("/activities")
        final_participants = final_response.json()["Chess Club"]["participants"]
        
        for participant in initial_participants:
            assert participant in final_participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_successful_unregister(self, client):
        """Test successful student unregistration"""
        email = "michael@mergington.edu"
        
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == f"Unregistered {email} from Chess Club"
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email not in activities["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Dance Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_not_signed_up(self, client):
        """Test unregister when not signed up returns 400"""
        email = "notsignedup@mergington.edu"
        
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Student not signed up for this activity"
    
    def test_unregister_preserves_other_participants(self, client):
        """Test that unregistering doesn't affect other participants"""
        email_to_remove = "michael@mergington.edu"
        email_to_keep = "daniel@mergington.edu"
        
        # Unregister one student
        client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email_to_remove}
        )
        
        # Verify other student still registered
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email_to_keep in activities["Chess Club"]["participants"]
        assert email_to_remove not in activities["Chess Club"]["participants"]
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signup and unregister"""
        email = "workflow_test@mergington.edu"
        activity_name = "Programming Class"
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == status.HTTP_200_OK
        
        # Verify signed up
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == status.HTTP_200_OK
        
        # Verify unregistered
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity_name]["participants"]
