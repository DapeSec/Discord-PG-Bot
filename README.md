# Family Guy Discord Bots

An interactive Discord bot system featuring Peter Griffin and Brian Griffin from Family Guy. The bots use the Mistral language model through Ollama to generate responses in their characteristic styles, complete with their unique personalities, and can interact with each other in a natural, entertaining way.

## Features

- Two distinct bots: Peter Griffin and Brian Griffin
- Each bot responds to direct messages and mentions
- Inter-bot communication allowing Peter and Brian to react to each other's messages
- Generates responses in each character's unique voice and style:
  - Peter: Humorous, dim-witted, with tangents and "Heheheh" interjections
  - Brian: Intellectual, sarcastic, and sometimes preachy
- Uses Ollama's Mistral model for AI responses
- Includes typing indicators for better user experience
- REST API endpoints for inter-bot communication

## Prerequisites

Before running the bots, make sure you have:

- Python 3.8 or higher installed
- [Ollama](https://ollama.ai/) installed and running
- Two Discord bot tokens (obtainable from the [Discord Developer Portal](https://discord.com/developers/applications))

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone [your-repository-url]
   cd discord-pg-bot
   ```

2. **Install required packages**
   ```bash
   pip install discord.py python-dotenv langchain-community flask requests
   ```

3. **Set up Ollama**
   - Install Ollama from [ollama.ai](https://ollama.ai/)
   - Pull the Mistral model:
     ```bash
     ollama pull mistral
     ```

4. **Configure Environment Variables**
   - Create a `.env` file in the project root
   - Add your Discord bot tokens and API URLs:
     ```
     DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
     DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here
     PETER_BOT_API_URL=http://localhost:5000/chat
     BRIAN_BOT_API_URL=http://localhost:5002/chat
     ```

5. **Run the Bots**
   Start both bots in separate terminal windows:
   ```bash
   python peter_bot.py
   python brian_bot.py
   ```

## Usage

### Interacting with Peter Griffin
- Send a message starting with `!peter` followed by your message
  ```
  !peter Tell me about your day
  ```
- Or mention Peter using @PeterGriffin followed by your message

### Interacting with Brian Griffin
- Send a message starting with `!brian` followed by your message
  ```
  !brian What's your opinion on literature?
  ```
- Or mention Brian using @BrianGriffin followed by your message

### Bot Interaction
When you interact with either bot, they will:
1. Generate their own response to your message
2. Automatically notify the other bot
3. The other bot will then respond to the conversation naturally

## Technical Details

### API Endpoints
- Peter's bot listens on port 5000
- Brian's bot listens on port 5002
- Both bots use Flask to handle inter-bot communication
- Each bot maintains its own Discord client connection

### Error Handling

The bots include comprehensive error handling for:
- Missing or invalid Discord tokens
- Ollama connection issues
- Inter-bot communication failures
- Message processing errors
- API endpoint issues

## Contributing

Feel free to fork the repository and submit pull requests for any improvements you'd like to add. Some areas for potential enhancement:
- Additional Family Guy characters
- More sophisticated conversation handling
- Enhanced error recovery
- Improved natural language processing

## License

[Your chosen license] 