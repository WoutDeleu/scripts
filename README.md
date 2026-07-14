### Personal Python Automation Scripts 🐍

Welcome to my collection of Python scripts designed to automate small tasks. These scripts make life easier by simplifying and streamlining various processes. Here's a brief overview of the scripts available:

#### MergeICS
- 📆 **Purpose**: Merges multiple iCalendar (ICS) files into a single file.
- 📥 **Usage**: Run the script and follow the prompts to select ICS files for merging.

#### SerieOrganiszer
- 📺 **Purpose**: Organizes local TV show files by renaming and structuring them.
- 📥 **Usage**: Run the script and follow the prompts to provide the folder containing your TV show files, and it will organize them by season and episode.

#### SubRenamer
- 📽️ **Purpose**: Renames subtitle files to match the video file they belong to.
- 📥 **Usage**: Run the script and follow the prompts to point to the folder containing video and subtitle files, and it will match and rename them.

#### GitManager
- 🌳 **Purpose**: Recursively scans a folder (including nested directories) for git repositories and either reports local changes or brings them up to date on their default branch.
- 📥 **Usage**: Run `python3 git_manager.py status <root_path>` to log every repo with local changes (staged, uncommitted, untracked, or unpushed commits), or `python3 git_manager.py update <root_path>` to check out the default branch (auto-detects `main`/`master`) and fast-forward pull each repo. Repos with local changes that would block an update are safely skipped and recorded. Every run prints a summary and writes a timestamped log file to the current directory.

Feel free to explore and use these scripts to make your daily tasks more efficient. If you have any questions, suggestions, or encounter issues, don't hesitate to reach out. Happy automating! 🤖🔧🚀
