@smoke @authentication
Feature: User Authentication
  As a user
  I want to authenticate securely
  So that I can access the system

  @positive @login
  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter valid username "testuser"
    And I enter valid password "password123"
    And I click the login button
    Then I should be redirected to the dashboard
    And I should see a welcome message

  @negative @login
  Scenario: Failed login with invalid password
    Given I am on the login page
    When I enter valid username "testuser"
    And I enter invalid password "wrongpass"
    And I click the login button
    Then I should see an error message "Invalid credentials"
    And I should remain on the login page
