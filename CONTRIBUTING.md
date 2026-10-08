# Team Contribution Guide

Welcome to the Smart HVAC project! To keep our codebase clean, prevent merge conflicts, and ensure we don't accidentally overwrite each other's work, we are using a standard **Pull Request (PR)** workflow. 

Please follow these steps to add your code, notes, or hardware schematics to the project:

## 1. Get the Latest Code
First, make sure you have the repository cloned to your computer:
```bash
git clone https://github.com/eternalshash/mind-overnight.git
cd mind-overnight
```

Always start by pulling the latest changes from our main integration branch. We are using **`develop`** as our shared working branch:
```bash
git checkout develop
git pull origin develop
```

## 2. Create Your Own Branch
**Never commit directly to `main` or `develop`!** Create a new branch for the specific task you are working on. Name it something descriptive:
```bash
git checkout -b your-name/feature-name
# Example: git checkout -b andy/power-delivery
```

## 3. Make Your Changes
Add your code, write your notes, or upload your hardware files to your branch. 

When you're ready to save your work, stage and commit your changes:
```bash
git add .
git commit -m "Brief description of what you added"
```

## 4. Push to GitHub
Push your new branch up to the GitHub repository:
```bash
git push -u origin your-name/feature-name
```

## 5. Submit a Pull Request (PR)
1. Go to the [GitHub repository page](https://github.com/eternalshash/mind-overnight) in your browser.
2. You will see a green button that says **"Compare & pull request"** next to your recently pushed branch. Click it!
3. **CRITICAL:** Change the **"base"** branch dropdown from `main` to `develop`. We want to merge your code into the working branch first for testing!
4. Add a quick title and description of what you did.
5. Click **"Create pull request"**.

## 6. Review & Merge
Shashwat will review the Pull Request, make sure there are no conflicts, and merge your code into the `develop` branch. Once everyone's pieces are working perfectly together in `develop`, we'll do one final merge into `main` for our project submission!
