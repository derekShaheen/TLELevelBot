# Discord Experience Bot

This bot provides an interactive way for users to gain experience and level up based on their activity in a Discord server.

## Experience Gain/Loss Conditions

The conditions for how experience is gained or lost are as follows:

- Experience is not issued if a user is blacklisted or if the member's status is idle and they are in a voice channel.

### On Member Sending a Message

- Experience per chat is calculated based on the number of messages sent within a time limit, the experience diminishing with each additional message sent within the limit. If the number of messages sent reaches the chat limit, the experience per chat reaches a minimum of 1.
- If the user is connected to a voice channel, the experience per chat is reduced by a factor of three.
- The experience gained is then added to the user's total, and their level is updated accordingly.

### On Voice Activity Check (Every Minute)

- If a member is connected to a voice channel (other than the AFK channel), their experience gain is calculated based on their activity:
    - If they are streaming, they receive a streaming bonus.
    - If they are alone in the channel, they receive a quarter of the experience per minute voice.
    - If all other members in the channel are idle, they receive a third of the experience per minute voice.
    - Otherwise, they receive the full experience per minute voice.
- The experience gained is then added to the user's total, and their level is updated accordingly.

In all cases, if a user's experience goes below 0, it is reset to 0.

After experience addition and level calculation, the user data is saved and the member's roles are adjusted if their level has changed. A level-up log message is also sent if their level has changed.

Experience gained per activity is rounded to two decimal places.

## Leaderboard System

The bot includes a leaderboard system that ranks users based on their experience. It generates an ASCII chart which is updated hourly and displays the top users in the server by rank.

![Leaderboard screenshot](https://i.imgur.com/aNte9Re.png)

The leaderboard includes:

- Usernames and rank, with special emojis representing the top three spots.
- The level and experience of each top user.

The leaderboard message is sent to a specified leaderboard channel in the server. The message is either edited if it already exists, or a new message is created.

The process of updating the leaderboard includes the following steps:

1. Load the guild data to obtain the leaderboard channel.
2. Generate the leaderboard using the `generate_leaderboard` function.
3. Try to fetch the existing leaderboard message. If it doesn't exist, a new one is created.
4. Update the leaderboard message with the newly generated ASCII chart.
5. Save the message ID to the guild data for future reference.

Please note that this process is performed for each guild that the bot is part of, every hour.

If you want to customize the frequency of leaderboard updates, you can adjust the update interval in the `tasks.loop(minutes=60)` decorator at the top of the `update_leaderboard` function.

## Administrator Commands

The bot includes the following administrator commands:

- `!set_level [member] [level]`: Set the level of a specific user.
- `!setrep [member] [experience]`: Adjust the reputation of a specific user.
- `!set_role [level] [role]`: Set a role for a specific level.
- `!set_channel [channel_type] [channel_name]`: Set a specific channel for certain notifications. Valid channel types are "leaderboard" or "publog".
- `!blacklist [user]`: Toggle blacklist status for a user. 

## User Commands

- `/rep [member]`: Displays the level and experience of a user. If no user is mentioned, it will display the level of the command user.

You can also right-click any user and view their rep from the menu.
![ShowRepContext](https://i.imgur.com/Gt0PlN8.png)

## Configuration

You can customize the bot's settings using the configuration file.

Here are the default settings:

```python
experience_constant: 1.5
experience_per_chat: 25
experience_per_minute_voice: 10
experience_streaming_bonus: 1
chat_limit: 5
```