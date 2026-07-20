// Script to sync repository labels
module.exports = async ({ github, context }) => {
  const labels = [
    // Type labels
    { name: 'type: feature', color: '0e8a16', description: 'New feature or enhancement' },
    { name: 'type: bug', color: 'd73a4a', description: 'Something is not working' },
    { name: 'type: documentation', color: '0075ca', description: 'Documentation updates' },
    { name: 'type: maintenance', color: 'fbca04', description: 'Code maintenance, refactoring' },
    { name: 'type: security', color: 'b60205', description: 'Security related' },
    { name: 'type: performance', color: '5319e7', description: 'Performance improvements' },
    { name: 'type: dependencies', color: '0366d6', description: 'Dependency updates' },
    { name: 'type: release', color: '0e8a16', description: 'Release related' },
    
    // Priority labels
    { name: 'priority: critical', color: 'b60205', description: 'Must be fixed immediately' },
    { name: 'priority: high', color: 'd93f0b', description: 'Should be addressed soon' },
    { name: 'priority: medium', color: 'fbca04', description: 'Normal priority' },
    { name: 'priority: low', color: '0e8a16', description: 'Nice to have' },
    
    // Status labels
    { name: 'status: blocked', color: '000000', description: 'Blocked by something else' },
    { name: 'status: in-progress', color: '0052cc', description: 'Currently being worked on' },
    { name: 'status: review-needed', color: '5319e7', description: 'Ready for review' },
    { name: 'status: waiting', color: 'bfd4f2', description: 'Waiting for input' },
    { name: 'status: duplicate', color: 'cfd3d7', description: 'Duplicate of another issue' },
    { name: 'status: wontfix', color: 'ffffff', description: 'Will not be fixed' },
    { name: 'status: stale', color: '6f6f6f', description: 'No activity for a while' },
    
    // Area labels
    { name: 'area: backend', color: '1d76db', description: 'Backend related' },
    { name: 'area: frontend', color: 'fbca04', description: 'Frontend related' },
    { name: 'area: api', color: '5319e7', description: 'API related' },
    { name: 'area: database', color: '0052cc', description: 'Database related' },
    { name: 'area: ui/ux', color: 'd4c5f9', description: 'UI/UX related' },
    { name: 'area: testing', color: 'bfdadc', description: 'Testing related' },
    { name: 'area: ci/cd', color: 'bfdadc', description: 'CI/CD related' },
    { name: 'area: devops', color: 'bfdadc', description: 'DevOps related' },
    { name: 'area: monitoring', color: 'bfdadc', description: 'Monitoring related' },
    { name: 'area: docs', color: '0075ca', description: 'Documentation' },
    { name: 'area: config', color: '6f6f6f', description: 'Configuration files' },
    
    // Size labels
    { name: 'size: xs', color: '0e8a16', description: 'Extra small (< 10 lines)' },
    { name: 'size: s', color: '7a5901', description: 'Small (10-50 lines)' },
    { name: 'size: m', color: 'fbca04', description: 'Medium (50-200 lines)' },
    { name: 'size: l', color: 'd93f0b', description: 'Large (200-500 lines)' },
    { name: 'size: xl', color: 'b60205', description: 'Extra large (> 500 lines)' },
    
    // Special labels
    { name: 'good first issue', color: '7057ff', description: 'Good for newcomers' },
    { name: 'help wanted', color: '008672', description: 'Extra attention needed' },
    { name: 'first-time-contributor', color: '6f6f6f', description: 'First contribution' },
    { name: 'automated-pr', color: '0075ca', description: 'Automatically generated PR' },
    { name: 'breaking-change', color: 'b60205', description: 'Contains breaking changes' },
    { name: 'wip', color: 'fbca04', description: 'Work in progress' },
    { name: 'needs-review', color: '5319e7', description: 'Needs code review' },
    { name: 'hacktoberfest', color: 'ff8c00', description: 'Hacktoberfest contribution' },
  ];

  // Get existing labels
  const { data: existingLabels } = await github.rest.issues.listLabelsForRepo({
    owner: context.repo.owner,
    repo: context.repo.repo,
  });

  // Create/update labels
  for (const label of labels) {
    const existing = existingLabels.find(l => l.name === label.name);
    
    if (existing) {
      if (existing.color !== label.color || existing.description !== label.description) {
        await github.rest.issues.updateLabel({
          owner: context.repo.owner,
          repo: context.repo.repo,
          name: label.name,
          color: label.color,
          description: label.description,
        });
        console.log(`Updated label: ${label.name}`);
      }
    } else {
      await github.rest.issues.createLabel({
        owner: context.repo.owner,
        repo: context.repo.repo,
        name: label.name,
        color: label.color,
        description: label.description,
      });
      console.log(`Created label: ${label.name}`);
    }
  }
};