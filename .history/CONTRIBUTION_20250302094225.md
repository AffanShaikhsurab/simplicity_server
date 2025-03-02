# CONTRIBUTING

## Welcome to Simplicity Blockchain!

Thank you for considering contributing to Simplicity Blockchain. This document outlines the process for contributing to the project and helps to make the contribution process straightforward and effective for everyone involved.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please report unacceptable behavior to the project maintainers.

- Be respectful and inclusive
- Be collaborative
- Focus on the best possible outcomes for the community
- Give and gracefully accept constructive feedback

## Getting Started

### Development Environment Setup

1. **Fork the repository** on GitHub
2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/your-username/simplicity-blockchain.git
   cd simplicity-blockchain
   ```
3. **Set up a remote upstream**:
   ```bash
   git remote add upstream https://github.com/original-owner/simplicity-blockchain.git
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r dev-requirements.txt  # Development dependencies
   ```
5. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/descriptive-branch-name
   ```

### Firebase Configuration

To test with data persistence:

1. Create a Firebase project at [firebase.google.com](https://firebase.google.com/)
2. Generate and download a service account key (JSON)
3. Place the JSON file in the project root directory
4. Set the environment variable for the credential file:
   ```bash
   # Linux/macOS
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-firebase-credentials.json"

   # Windows (Command Prompt)
   set GOOGLE_APPLICATION_CREDENTIALS=path\to\your-firebase-credentials.json

   # Windows (PowerShell)
   $env:GOOGLE_APPLICATION_CREDENTIALS="path\to\your-firebase-credentials.json"
   ```

## Development Workflow

### Branching Strategy

- `main` - Main branch containing stable code
- `develop` - Development branch for ongoing work
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `docs/*` - Documentation updates

### Making Changes

1. Ensure your branch is up to date with the upstream:
   ```bash
   git fetch upstream
   git rebase upstream/develop
   ```
2. Make your changes
3. Write or update tests as necessary
4. Run the test suite:
   ```bash
   pytest
   ```
5. Follow the code style guidelines
6. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat: add support for transaction batching"
   ```

### Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, indentation)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Pull Requests

1. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature
   ```
2. **Submit a pull request** to the `develop` branch of the original repository
3. **Fill in the PR template** with all relevant information
4. **Request a review** from one of the maintainers
5. **Update your PR** as needed based on feedback

## Code Standards

### Python Style Guide

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions
- Maximum line length of 88 characters (compatible with Black formatter)
- Use type hints where appropriate
- Use docstrings (Google style) for functions, classes, and modules

### Linting and Formatting

Before submitting changes, run:

```bash
# Format code
black .

# Check style
flake8 .

# Sort imports
isort .

# Type checking
mypy .
```

### Documentation

- Update documentation for any new or modified functionality
- Include docstrings for all public classes and functions
- Follow the Google docstring format:
  ```python
  def function_with_types_in_docstring(param1, param2):
      """Example function with types documented in the docstring.

      Args:
          param1 (int): The first parameter.
          param2 (str): The second parameter.

      Returns:
          bool: The return value. True for success, False otherwise.
      """
      return True
  ```

## Testing

- Write unit tests for all new functionality
- Ensure all tests pass before submitting a pull request
- Maintain or improve code coverage
- Test edge cases and error conditions

## Issue Reporting

### Bug Reports

When filing a bug report, include:

1. A clear title and description
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Environment details (OS, Python version, etc.)
6. Logs or error messages

### Feature Requests

When submitting a feature request:

1. Describe the feature in detail
2. Explain why it would be valuable
3. Provide examples of how it would be used
4. Indicate if you're willing to work on implementing it

## Review Process

1. Maintainers will review your PR for:
   - Correctness
   - Test coverage
   - Code quality
   - Documentation
   - Adherence to project standards
2. Address feedback through additional commits
3. Once approved, a maintainer will merge your PR

## Areas for Contribution

We welcome contributions in several areas:

### Core Blockchain Components

- Consensus algorithm improvements
- Block validation enhancements
- Transaction processing optimizations
- Cryptographic implementation security

### Networking and Node Management

- Node discovery mechanisms
- P2P communication protocols
- Network resilience and fault tolerance
- TTL and node health monitoring

### User Experience

- API improvements
- CLI tools
- Transaction verification UX
- Wallet functionality

### Educational Content

- Code comments
- Examples and tutorials
- Diagrams and visualizations
- Interactive demos

### Performance and Scalability

- Transaction throughput
- Database optimizations
- Memory usage improvements
- Caching strategies

## Communication

- **GitHub Issues**: For bug reports, feature requests, and discussions
- **Pull Requests**: For code contributions
- **Discussions**: For general questions and community interaction
- **Email**: For security concerns or private communications

## License

By contributing, you agree that your contributions will be licensed under the project's license.



Thank you for contributing to Simplicity Blockchain!


```
