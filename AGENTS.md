# instructions for agents
## messages from the user
1. the file EXECUTION_PLAN.md contains the development plan. This file will influence your operations and decisions on development
2. the PROGRESS.md file records progress from previous sessions. Each time you are prompted by the user review the EXECUTION_PLAN.md and PROGRESS.md files for relevant information
3. after completing each step from the EXECUTION_PLAN.md stop execution and update the PROGRESS.md file with a summary of your actions for the completion of the step, as well as your intended next steps for continuity between sessions. Next inform the user of your status and ask the user any clarifying questions you have about the next step in the execution plan. If no questions proceed with the next section of the plan.
4. review the file LOG_BOOK.md. this file will be used to log each of the tasks that the agent (you) have completed. For each feature or fix you complete append a new section to the LOG_BOOK.md file in the following format:
```
## name of feature or fix | date of completion
1 or 2 sentence description of the feature or fix.
```
Always use a python virtual env for python if not in a container.
