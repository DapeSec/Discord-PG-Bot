# Peter Griffin Discord Bot

A fun and interactive Discord bot that channels Peter Griffin's personality from Family Guy. The bot uses the Mistral language model through Ollama to generate responses in Peter Griffin's characteristic style, complete with his signature humor, tangents, and pop culture references.

## Features

- Responds to messages starting with `!chat`
- Responds to direct mentions
- Generates responses in Peter Griffin's voice and style
- Uses Ollama's Mistral model for AI responses
- Includes typing indicators for better user experience

## Prerequisites

Before running the bot, make sure you have:

- Python 3.8 or higher installed
- [Ollama](https://ollama.ai/) installed and running
- A Discord bot token (obtainable from the [Discord Developer Portal](https://discord.com/developers/applications))

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone [your-repository-url]
   cd discord-pg-bot
   ```

2. **Install required packages**
   ```bash
   pip install discord.py python-dotenv langchain-community
   ```

3. **Set up Ollama**
   - Install Ollama from [ollama.ai](https://ollama.ai/)
   - Pull the Mistral model:
     ```bash
     ollama pull mistral
     ```

4. **Configure Environment Variables**
   - Create a `.env` file in the project root
   - Add your Discord bot token:
     ```
     DISCORD_BOT_TOKEN=your_discord_bot_token_here
     ```

5. **Run the Bot**
   ```bash
   python discord_bot.py
   ```

## Usage

- Send a message starting with `!chat` followed by your message to interact with Peter Griffin
  ```
  !chat Tell me about your day
  ```
- Alternatively, mention the bot using @BotName followed by your message

## Error Handling

The bot includes comprehensive error handling for:
- Missing Discord token
- Invalid Discord token
- Ollama connection issues
- Message processing errors

## Contributing

Feel free to fork the repository and submit pull requests for any improvements you'd like to add.

## License

[Your chosen license] 