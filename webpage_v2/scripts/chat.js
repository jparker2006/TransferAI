/* Chat window renderer for TransferAI */

/**
 * Return the chat input bar HTML.
 * @returns {string}
 */
function renderInputBar() {
    let s = "<div class='ChatInputContainer'>";
    s += "  <div class='ChatInputInner'>";
    s += "    <i class='fas fa-microphone MicIcon' id='MicIcon'></i>";
    s += "    <textarea id='UserInput' rows='1' class='ChatInput' placeholder='Ask me anything...'></textarea>";
    s += "    <i class='fas fa-paper-plane SendIcon sendDisabled' id='SendIcon'></i>";
    s += "  </div>";
    s += "</div>";
    return s;
}

/**
 * Return pre-defined sample conversation HTML.
 * @returns {string}
 */
function renderSampleConversation() {
    let s = '';
    // User bubble
    s += "<div class='ChatBubble user'>Will CSCI 10 transfer to UCSD?</div>";

    // CourseSearchTool card
    s += "<div class='ToolCard'>";
    s += "  <div class='ToolCardHeader'><i class='fas fa-search'></i><span>Course Search</span><span class='ToolName'>[CourseSearchTool]</span></div>";
    s += "  <p>I queried ASSIST and confirmed CSCI 10 at SMC transfers as CSE 8A at UCSD.</p>";
    s += "</div>";

    // PrereqGraphTool card
    s += "<div class='ToolCard'>";
    s += "  <div class='ToolCardHeader'><i class='fas fa-project-diagram'></i><span>Prerequisite Graph</span><span class='ToolName'>[PrereqGraphTool]</span></div>";
    s += "  <p>MATH 31 → CS 8 → CSE 8A</p>";
    s += "</div>";

    // AuditBuilder card
    s += "<div class='ToolCard'>";
    s += "  <div class='ToolCardHeader'><i class='fas fa-clipboard-check'></i><span>Transfer Audit</span><span class='ToolName'>[AuditBuilder]</span></div>";
    s += "  <p>This course should transfer successfully!</p>";
    s += "</div>";

    return s;
}

/**
 * Build and return entire chat panel HTML.
 * @returns {string}
 */
export function renderChat() {
    let sChat = "<div class='MainContent'>";
    // Header section
    sChat += "  <div class='ChatHeader'>";
    sChat += "    <h1>👋 Hi Ryan!</h1>";
    sChat += "  </div>";

    // Scrollable chat body
    sChat += "  <div class='ChatArea'></div>";

    // Input bar
    sChat += renderInputBar();

    sChat += "</div>";

    return sChat;
}

/**
 * Attach behaviour to input bar: enable/disable send icon.
 */
export function setupChatInput() {
    const inputEl = document.getElementById('UserInput');
    const sendIcon = document.getElementById('SendIcon');
    if (!inputEl || !sendIcon) return;

    const toggleSend = () => {
        if (inputEl.value.trim().length > 0) {
            sendIcon.classList.remove('sendDisabled');
        } else {
            sendIcon.classList.add('sendDisabled');
        }
    };

    inputEl.addEventListener('input', toggleSend);
    toggleSend();

    // Optional: simple click placeholder
    sendIcon.addEventListener('click', () => {
        if (sendIcon.classList.contains('sendDisabled')) return;
        // TODO: integrate message sending in future.
        inputEl.value = '';
        toggleSend();
    });
} 