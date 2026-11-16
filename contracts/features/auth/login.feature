@SEED-1
Feature: User can register and log in
  The user approved the scenario wording and AC-1/AC-2 mapping for seed-1-approved-v1.
  SEED-1 and the supplied AC-3 identifier are preserved.

  Background:
    Given the immutable synthetic baseline user exists
    And a fresh browser context has no authentication state

  @AC-1
  Scenario: Register a unique user
    Given a new registration identity unique to this execution and matrix slot
    When I open the registration page
    And I fill "register.username", "register.email", and "register.password" with that identity
    And I activate "register.submit"
    Then registration returns a user and a token
    And the browser has an authenticated session for that identity
    And "account.identity" shows that identity's email on the protected settings page

  @AC-2
  Scenario: Log in with valid credentials
    When I open the login page
    And I fill "login.email" and "login.password" with the baseline credentials
    And I activate "login.submit"
    Then login returns the baseline user and a token
    And the browser has an authenticated session for the baseline user
    And "account.identity" shows the baseline email on the protected settings page

  @AC-3
  Scenario: Reject an invalid password without creating a session
    When I open the login page
    And I fill "login.email" with the baseline email and "login.password" with an invalid password
    And I activate "login.submit"
    Then "login.error" displays "Email or password is invalid."
    And the browser still has no authentication state
    When I navigate directly to the protected settings page
    Then access is denied and the browser is redirected to the login page
    And "login.heading" is visible and "account.identity" is absent
