# CPR Bot

A calibrated peer review Discord bot that assists the process of coordinating and evaluating peer reviews of student work.

## Running the Project

There are two ways to run the project. The easiest way is to simply invite the bot to your server and use `/help` in any channel to start.

However, if you wish to run your own instance of the bot, please continue reading.

**Step 1:** Visit the [Discord Developer Portal](https://discord.com/developers/applications) and create an application. Any name is fine, you can change it later.

**Step 2:** Select your application and navigate to `Bot` on the left hand side, then `Add Bot` and select a name for your bot.

**Step 3:** Save the `Token`. This is your bot token will be required by your `config.yml` file (see step 10).

**Step 4:** On the left hand side, select `OAuth2` > `URL Generator`.

**Step 5:** Tick on the following items:

1. Scopes:
- bot 
- application.commands

2. Bot Permissions:
- Administrator (required to manage channel permissions)

**Step 6:** Copy the content in the `Generated URL` right below. Copy it to your browser's address bar and add the bot to your server.

**Step 7:** Install [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/).

**Step 8:** Clone the repository.

**Step 9:** At the root of the directory, create a `.env` file using `.env_example` as the templates and fill out the variables.

**Step 10:** Navigate to `scripts` and run `sh build-app.sh`.

Your bot should be up and running.

## Contributing

Contributors are more than welcome to improve the project by creating a new issue to report bugs, suggest new features, or make changes to the source code by making a pull request. To have your work merged in, please make sure the following is done:

1. Fork the repository and create your branch from master.
2. If you’ve fixed a bug or added something new, add a comprehensive list of changes.
3. Ensure that your code is tested, functional, and is linted.
