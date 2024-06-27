![Windows Compatibility](https://img.shields.io/badge/Windows-10%2C%2011-blue)
![Linux Compatibility](https://img.shields.io/badge/Linux-Compatible-green)

# Coomer Downloader App

Coomer Downloader App is a desktop application developed in Python that allows users to easily download images and videos from URLs. The application provides an intuitive graphical user interface (GUI) to simplify the process.

## Table of Contents

- [Features](#features)
- [Supported Pages](#supported-pages)
- [Contributing](#contributing)
- [Community](#community)
- [Usage](#usage)
- [Clone and Setup](#clone-and-setup)
- [Downloads](#downloads)

## Features

### Downloading images and videos

Coomer Downloader App supports downloading both images and videos efficiently. Users can simply enter the URL of the media they want to download, and the app will handle the rest. It ensures a smooth downloading experience by supporting multiple threads for faster downloads, providing progress updates, and handling various file formats including .jpg, .png, .mp4, and .mkv. Additionally, the app can manage large download queues.

## Supported Pages

- [coomer.su](https://coomer.su/)
- [kemono.su](https://kemono.su/)
- [erome.com](https://www.erome.com/)
- [bunkr-albums.io](https://bunkr-albums.io/) (images only)

## Community

If you have any issues or want to communicate with me, join my Discord server by clicking the button below:

[![Join Discord](https://img.shields.io/badge/Join-Discord-7289DA.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ku8gSPsesh)

## Downloads

- **Download the Latest Version**: Visit the [releases page](https://github.com/Emy69/CoomerDL/releases) to download the latest version of the application.

## Usage

1. Open the application.
2. Enter the URL of the image or video you want to download.
3. Click the download button and wait for the process to complete.

[![Usage GIF](https://github.com/Emy69/CoomerDL/blob/main/resources/screenshots/0627.gif)

## Clone and Setup

### Prerequisites

- Python 3.8 or higher.

### Warning

- In some Linux distributions, tkinter may not be installed by default. You might need to install it manually.

### For Windows

1. **Clone the repository**

    ```bash
    git clone https://github.com/Emy69/CoomerDL.git
    cd CoomerDL
    ```

2. **Install the dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Usage**

    ```bash
    python main.py
    ```

### For Linux

1. **Clone the repository**

    ```bash
    git clone https://github.com/Emy69/CoomerDL.git
    cd CoomerDL
    ```

2. **Install the dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Install tkinter if not installed**

    - For Debian/Ubuntu based distributions:

        ```bash
        sudo apt-get install python3-tk
        ```

    - For Red Hat/Fedora based distributions:

        ```bash
        sudo dnf install python3-tkinter
        ```

4. **Usage**

    ```bash
    python main.py
    ```

## Contributing

Contributions are welcome! If you are interested in enhancing the Coomer Downloader App, please follow these steps to contribute:

1. **Fork the Repository**
   - Start by forking the project to your GitHub account. You can do this by visiting the [main page of the repository](https://github.com/Emy69/CoomerDL) and clicking the fork button.

2. **Create a Branch**
   - Create a branch in your forked repository for your changes:

     ```bash
     git checkout -b feature-branch-name
     ```

3. **Make Your Changes**
   - Implement your changes and enhancements in your feature branch. Ensure you adhere to the coding standards and guidelines of the project.

4. **Run Tests**
   - If the project has tests, run them to ensure your changes do not break existing functionality.

5. **Submit a Pull Request**
   - Once ready, submit a pull request from your fork back to the original repository. Provide a clear description of your changes and any other information that might help the reviewers understand your contributions.

6. **Wait for Feedback**
   - The project maintainers will review your pull request. Based on their feedback, you might need to make additional changes.

### Getting Help

If you need help with your contributions, feel free to raise issues on the project's issue tracker or contact the maintainers directly.

