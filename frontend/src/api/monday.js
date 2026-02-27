// API layer for communicating with the FastAPI backend

import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:7860";

/**
 * Send a user query to the backend and get the agent's response.
 * @param {string} message - The user's question
 * @param {Array} history - Conversation history array
 * @returns {Promise<Object>} - { answer, action_trace, data_quality_report }
 */
export async function sendQuery(message, history) {
    const response = await axios.post(`${API_BASE_URL}/query`, {
        message,
        history,
    });
    return response.data;
}
