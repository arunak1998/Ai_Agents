# Agentic AI Travel Planner

An AI-powered travel planning assistant that builds complete, real-time trip itineraries using LangGraph, OpenAI, and real-world APIs. It follows the Agentic RAG pattern (React + Action) and includes a Streamlit frontend for seamless user interaction.

## 🚀 Features

- Accepts natural queries like:
  `Plan a 6-day trip to London under ₹1,00,000 with flights and hotels`
- Generates a complete day-by-day itinerary
- Recommends attractions using real-time Google Places data
- Suggests restaurants and local food spots
- Searches for hotels with live prices
- Finds round-trip flights using Skyscanner API
- Adds weather forecast per city and per day
- Converts budget into detailed category-wise estimates (stay, food, transport)
- Exports the trip plan as a Markdown file

## ⚙️ Tech Stack

- LangGraph: for building the agent with React + Action design
- LangChain: tools, memory, and structured agent execution
- OpenAI GPT-4o: for planning and Markdown generation
- Streamlit: for the interactive web frontend
- APIs used:
  - Google Places API (hotels, attractions, food)
  - Skyscanner API (flights)
  - OpenWeather API (weather)
  - ExchangeRate API (currency conversion)

## 🧱 Architecture

The app is structured as:

- `src/agent/`: LangGraph-based agent with tool definitions
- `src/utils/`: External service utilities (weather, currency, budget)
- `streamlit_app.py`: Frontend to interact with the agent
- `requirements.txt`: Dependencies
