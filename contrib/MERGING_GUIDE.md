# Merging Guide
This guide exists to help onboard new people to the process of syncing Elements with Bitcoin Core.

## Setup
1. Fork the Elements repository on GitHub.
2. Clone your forked repository to your local machine.
3. Add the original Elements and Bitcoin Core repositories as remotes, and also add the repositories of your collaborators to the remotes:
```bash
git remote add upstream git@github.com:ElementsProject/elements.git
git remote add bitcoin git@github.com:bitcoin/bitcoin.git
```
4. Fetch the latest changes from the original repositories:
```bash
git fetch upstream
git fetch bitcoin
```
5. Create a new branch from where you want to start your work (usually `merging`):
```bash
git checkout -b merging
```
6. Install the necessary dependencies and set up your development environment according to the project's documentation. Specifically, the `Building` section of the [doc/README](../doc/README.md) file.
7. Modify [merge-prs.sh](./merge-prs.sh) to include the PRs you want to merge. The script will automatically merge the specified PRs from Bitcoin Core into your current branch. In particular, the `WORKTREE`, `PARALLEL_BUILD` and `PARALLEL_TEST` variables should be set according to your environment and needs.
8. Run the setup command from project root:
```bash
./contrib/merge-prs.sh setup
```
9. Go to the newly created worktree and build the project at least once to ensure everything is set up correctly.

## Syncing with others
Let's say you have a remote of your colleague called `steve` and you want to sync the changes he made to the `merged-master` branch. You can do it by running:
```bash
git fetch steve
git push origin steve/merged-master:merged-master
git pull origin merged-master
```

## Merging Process
The merging process involves several steps to ensure that the changes from Bitcoin Core are properly integrated into Elements. Here’s a general outline of the process.

Note: All instances of `./contrib/merge-prs.sh` should be run from the root of the project (i.e., your `merging` branch). Any manipulation of changes should be done in the `merged-master` worktree.

Start merging the PRs with the command:
```bash
./contrib/merge-prs.sh go
```

There are several cases that can happen now:
1. The PRs are merged successfully without any conflicts and all tests pass. In this case, the script proceeds to the next PR until all PRs are merged.
2. There are merge conflicts. In this case, the script will stop and you will need to resolve the conflicts manually. All conflict resolution happens in the `merged-master` worktree. Once you have added all resolved changes with `git add`, finish merging with `git merge --continue`. After resolving the conflicts, you can continue the merging process by running:
```bash
./contrib/merge-prs.sh continue
```
3. There are no merge conflicts, but some tests fail. In this case, the script will stop and you will need to investigate the test failures. You can run the tests locally to identify the issues and fix them. If only Python tests failed, you can just run them via terminal and count them as passed, but if C++ tests failed, you should rebuild everything and run them again. After you have fixed everything, you should double check if all processes behave accordingly with:
```bash
./contrib/merge-prs.sh step-continue
```
4. C++ is not compiling. In this case, you will need to investigate the compilation errors and fix them. After you have fixed everything, you should double check if all processes behave accordingly with:
```bash
./contrib/merge-prs.sh step-continue
```

In cases 3 and 4, you should amend changes to a previous commit and continue merging:
```bash
git commit --amend --no-edit
./contrib/merge-prs.sh go # no need to run 'continue' again, we have already done it with 'step-continue'
```

## Common Issues
1. Because of how Elements works, you might need to rewrite some new Bitcoin logic with primitives and basic logic that Elements has.
2. You need to keep in mind that witness is written a little bit differently in Elements, the transaction fee is also a separate output, and the transaction structure itself is a little bit different. This can all affect, for example, static tests that hardcoded some prehashed transactions or block hashes. Some new tests might all need to be rewritten, but they should still reflect the same logic as in Bitcoin Core. Simply discarding tests is a very bad idea and it can sabotage the whole process.
3. Often there will be conflicts in the core spending logic of Elements. If you're not sure how it is supposed to work, ask someone who is more familiar with the codebase. It is very important to keep the logic of Elements intact, otherwise we can break some features and it will be very hard to fix them later on. You should always mark Elements specific changes with a `# ELEMENTS: reason` comment, so it will be easier to identify them later on and also to avoid conflicts with Bitcoin Core changes.
