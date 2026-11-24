# Three-Minute Judge Demo Script

## 0:00-0:25: Introduction

"This is Boot-to-Browser: a voice-controlled co-pilot that lets a visually impaired user operate the computer from spoken goals. It does not rely on the DOM or accessibility tree. It captures the real screen, adds numbered Set-of-Mark boxes, asks the cloud reasoning model for the next action, applies safety checks, executes the action, and verifies what changed."

## 0:25-0:50: Startup

"On startup, the system opens a browser, plays a readiness chime, and says 'Co-pilot ready.' I can now press F9 and speak a goal."

Press F9. Say: "Open the local demo form."

"The system captures the screen and planning begins. Each visible control receives a numbered box, so the model makes a grounded choice instead of guessing from the page DOM."

## 0:50-1:35: Goal execution

Press F9. Say: "Fill the name field with Alex and the email field with alex@example.com."

"The agent follows observe, plan, safety gate, act, and verify repeatedly. It can click, type, scroll, press keys, wait, ask for help, or stop."

Allow the agent to enter the fields. If it pauses before submitting, explain that the action is sensitive.

## 1:35-2:05: Confirmation moment

When the confirmation prompt appears, say: "Do not confirm yet."

Then say: "Now say confirm."

Say clearly: "Confirm."

"This is the confirmation gate. Submitting, deleting, sending, buying, or changing sensitive information requires explicit confirmation. Silence or another answer cancels the action."

If available, let the form submit and show the confirmation message.

## 2:05-2:30: Stop moment

Press F9 and start a longer goal: "Open several pages and keep moving through the browser."

After the first action begins, press **Ctrl+Shift+X**.

"Ctrl+Shift+X is the global stop control. It also works while desktop actions or speech are running. The stop listener recognizes the spoken word 'stop,' interrupts queued speech, sets the abort flag, and prevents further actions."

## 2:30-2:50: Safety and evaluation

"The project also has a maximum of 20 steps, two unchanged-screen retries, three-identical-action detection, and append-only JSONL logs. Passwords and OTPs are never typed or sent to the cloud model."

## 2:50-3:00: Closing

"Evaluation covers 12 tasks, including a local form, a denied confirmation, deletion, scrolling, search, Gmail, and stopping mid-task. The evaluator records grounding accuracy, completion rate, retries, and latency. Boot-to-Browser is a safe, accessible, screen-grounded computer co-pilot."
