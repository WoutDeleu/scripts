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

#### HolidayCalculator
- **Purpose**: Calculates holiday days still to take before year end in Belgium, excluding weekends and Belgian public holidays and accounting for meeruren earned only on worked days.
- **Dependency**: Install with `python3 -m pip install holidays`.
- **Usage**: Run `./holiday_calculator.py` for interactive prompts (press Enter at the date prompt to use today), or supply any/all inputs: `./holiday_calculator.py --date 18-10-2026 --legal-hours 38 --recup-days 2 --booked-days 3 --meeruren 6.8`. Dates use `DD-MM-YYYY`. Legal holiday and meeruren are in hours; recup and booked holiday are in days. Fractional days are supported. Booked days must already be deducted from the balances and only reduce working days here.
- **Calculation**: With `H = legal_hours + recup_days * 7.6 + meeruren` and remaining working days `W`, days still to take are `D = (H + 0.4 * W) / 8`. The breakdown includes public holiday names and projected accrual. Rounded-down full-day and half-day figures are alternatives, not additive (for example, 9.95 days becomes 9 full days or 9.5 days in half-day increments). If `D > W`, it warns without capping D; the formula's negative projected accrual then indicates an infeasible schedule.
- **Tests**: Install pytest with `python3 -m pip install pytest`, then run `python3 -m pytest -q test_holiday_calculator.py`.

Feel free to explore and use these scripts to make your daily tasks more efficient. If you have any questions, suggestions, or encounter issues, don't hesitate to reach out. Happy automating! 🤖🔧🚀
