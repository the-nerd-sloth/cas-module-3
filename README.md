<a id="readme-top"></a>

<div align="center">

# Advanced Machine Learning CAS - Module 3

![GitHub Repo Badge](https://img.shields.io/badge/github-repo-blue?logo=github)
[![License: Unlicense](https://img.shields.io/badge/License-Unlicense-blue.svg)](./LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![made-with-latex](https://img.shields.io/badge/Made%20with-LaTeX-1f425f.svg)](https://www.latex-project.org/)
[![Github all releases](https://img.shields.io/github/downloads/Naereen/StrapDown.js/total.svg)](https://GitHub.com/Naereen/StrapDown.js/releases/)

Module 3 of the Advanced Machine Learning Certificate of Advanced Studies of University of Bern.

</div>

## Table of Contents

- [About](#about)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Design Notes](#design-notes)
- [Authors](#authors)
- [License](#license)

## About

This project includes an implementation involving an agent-based system designed to process and analyze cancer-related data and statistics. It illustrates the strengths, limitations, and real-world applicability of agentic architectures in handling complex, data-driven tasks within the healthcare domain.

[Back to top](#readme-top)

## Project Structure

```text
.
├── agent/                # Local Ollama-based agent implementation
├── presentation/         # Project's presentation
├── LICENSE               # Project's license
└── README.md             # Main project documentation
```

[Back to top](#readme-top)

## Getting Started

### Prerequisites

- Git
- Python 3.12+

### Preparation

```sh
git clone git@github.com:the-nerd-sloth/cas-module-3.git
cd cas-module-3/agent
```

[Back to top](#readme-top)

## Usage

Follow the instructions in the agent's [README](./agent/README.md) file.
Generic flow (after the agent has been set up):
1. Run `python main.py collect` to download the data and prepare the database.
2. Run `python main.py chat` for an interactive chat.
3. Use the command `exit` to quit the chat.

[Back to top](#readme-top)

## Design Notes

- Instead of one big loop for the data acquisition and chat functionality, the Agent was split.
- As the data imported are fairly static, this does not violate the definition of Agentic AI.

[Back to top](#readme-top)

## Authors

- **Spyridon Margomenos**
  - GitHub: [@the-nerd-sloth](https://github.com/the-nerd-sloth)

[Back to top](#readme-top)

## License

Distributed under The Unlicense license. For more information see [LICENSE](./LICENSE).

[Back to top](#readme-top)
