/* Main boot logic for TransferAI Chat UI */
import { renderSidebar, setupSidebarInteractions } from './sidebar.js';
import { renderChat } from './chat.js';
import { setupChatInput } from './chat.js';

/**
 * Render the main chat page once DOM is ready.
 */
function ChatPage() {
    let sPage = '';
    // Assemble sidebar and main chat area
    sPage += renderSidebar();
    sPage += renderChat();

    const body = document.getElementById('Body');
    if (body) {
        body.innerHTML = sPage;
        setupChatInput();
        setupSidebarInteractions();
    }
}

document.addEventListener('DOMContentLoaded', ChatPage);

// Export in case other modules need to re-render
export { ChatPage }; 