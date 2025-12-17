Feature: User Login
  As a registered user
  I want to log in to the application
  So that I can access my account

  Background:
    Given the application is running
    And I am on the login page

  @smoke @authentication
  Scenario: Successful login with valid credentials
    Given I have a valid username "testuser"
    And I have a valid password "password123"
    When I enter my credentials
    And I click the login button
    Then I should be redirected to the dashboard
    And I should see a welcome message "Welcome, testuser"

  @negative @authentication
  Scenario: Failed login with invalid password
    Given I have a valid username "testuser"
    And I have an invalid password "wrongpassword"
    When I enter my credentials
    And I click the login button
    Then I should see an error message "Invalid credentials"
    And I should remain on the login page

  @edge-case
  Scenario Outline: Login attempts with various credentials
    Given I have username "<username>"
    And I have password "<password>"
    When I enter my credentials
    And I click the login button
    Then I should see result "<result>"

    Examples:
      | username  | password    | result                |
      | admin     | admin123    | Dashboard             |
      | testuser  | test123     | Dashboard             |
      | invalid   | invalid123  | Invalid credentials   |
      | empty     |             | Password required     |
