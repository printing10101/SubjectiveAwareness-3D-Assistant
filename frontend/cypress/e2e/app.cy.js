/* eslint-env mocha */
describe('Application Smoke Test', () => {
  it('loads the welcome page successfully', () => {
    cy.visit('/')
    cy.contains('AI辅助分析系统').should('be.visible')
    cy.contains('开始使用').should('be.visible')
  })

  it('navigates to main page after clicking start button', () => {
    cy.visit('/')
    cy.contains('开始使用').click()
    cy.url().should('include', '/main')
  })
})