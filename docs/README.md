# Qubinode Navigator Documentation

This directory contains the Jekyll-based documentation website for Qubinode Navigator.

## Which Guide Should I Use?

- **Quick 15-min setup?** - [QUICKSTART.md](../QUICKSTART.md)
- **Fresh OS install?** - [CLEAN-INSTALL-GUIDE.md](CLEAN-INSTALL-GUIDE.md)
- **Development/contributing?** - [GETTING_STARTED.md](GETTING_STARTED.md)
- **Production deployment?** - [Deploy to Production](how-to/deploy-to-production.md)
- **MCP server integration?** - [MCP Production Setup](tutorials/mcp-production-and-client.md)

## Local Development

To run the documentation site locally:

```bash
cd docs
bundle install
bundle exec jekyll serve
```

The site will be available at `http://localhost:4000`

## Deployment

The documentation is automatically deployed to GitHub Pages via GitHub Actions when changes are pushed to the `main` branch.

**Live Site**: https://qubinode.github.io/qubinode_navigator

## Structure

### Published to Site

- `_config.yml` - Jekyll configuration
- `index.markdown` - Homepage
- `explanation/` - Conceptual discussions (architecture, design decisions)
- `how-to/` - Task-oriented guides (deploy, contribute, release)
- `tutorials/` - Learning-oriented step-by-step guides
- `reference/` - API documentation and technical reference
- `guides/` - Operational guides (RAG, multi-agent LLM)
- `fixes/` - Known issues and solutions

### Excluded from Site (Available on GitHub)

- `adrs/` - Architecture Decision Records (excluded due to Jinja2/Liquid conflicts)
- `deployments/` - Platform-specific deployment guides
- `development/` - Developer documentation
- `plugins/` - Plugin documentation
- `security/` - Security guides
- `vault-setup/` - Vault integration guides

## Theme

This site uses the [Just the Docs](https://just-the-docs.com/) theme for clean, searchable documentation.

## Contributing

When adding new documentation:

1. Follow the existing structure and naming conventions
1. Add appropriate front matter to new pages
1. Update navigation in `_config.yml` if needed
1. Test locally before committing
1. The site will auto-deploy after merging to main

## Troubleshooting

If the site isn't building:

1. Check the GitHub Actions workflow status
1. Verify Jekyll syntax with `bundle exec jekyll build`
1. Ensure all required gems are in the Gemfile
1. Check for any broken internal links
