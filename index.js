"use strict";

var g_objUserData = {};

const Page = {
    LANDING: "landing",
    LOGIN: "login",
    SIGNUP: "signup",
    DASHBOARD: "dashboard",
    AICHAT: "aichat"
};

onload = () => {
    // AIChatPage();
    LandingPage();
//     DashboardPage();
}


// Landing Page Stuff

const LandingPage = () => {
    let sPage = "";
    sPage += "<div class='MainContainer FadeInLanding'>";
    sPage += NavBar(Page.LANDING);
    sPage += Hero();
    sPage += HowItWorks();
    sPage += ChatbotPreview();
    sPage += StickyCTA();
    sPage += "</div>";
    sPage += Footer();
    document.getElementById('Body').innerHTML = sPage;
}

const NavBar = (currentPage) => {
  let sPage = "";

  const navContainerClass = currentPage === Page.AICHAT ? "NavBarContainer NavContainerShrunkForAI" : "NavBarContainer";
  sPage += `<div class='${navContainerClass}'>`;

  const navClass = currentPage === Page.AICHAT ? "NavBar NavBarShrunkForAI" : "NavBar";
  sPage += `<div class='${navClass}'>`;

  // ✅ Logo wrapper — add extra class only for AICHAT
  const logoClass = currentPage === Page.AICHAT ? "LogoWrapper LogoAlignedWithSidebar" : "LogoWrapper";
  sPage += `<div class='${logoClass}'>`;

  // ✅ Logo image
  switch (currentPage) {
    case Page.LANDING:
      sPage += "<img class='LogoImage' src='logo.png' alt='TransferAI logo'>";
      break;
    case Page.LOGIN:
    case Page.SIGNUP:
      sPage += "<img class='LogoImage clickable' src='logo.png' alt='TransferAI logo' onclick='LandingPage()'>";
      break;
    case Page.DASHBOARD:
      sPage += "<img class='LogoImage' src='logo.png' alt='TransferAI logo'>";
      break
    case Page.AICHAT:
      sPage += "<img class='LogoImage clickable' src='logo.png' alt='TransferAI logo' onclick='DashboardPage()'>";
      break;
    default:
      break;
  }

  // ✅ Sidebar toggle button (only on AICHAT)
  if (currentPage === Page.AICHAT) {
    sPage += `
    <button class='SidebarToggleButton NavCollapseButton' onclick='toggleSidebar()'>
        <svg class='ChevronIcon' xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'>
        <rect x='3' y='3' width='18' height='18' rx='6' ry='6' stroke='currentColor' fill='none' stroke-width='2'/>
        <path d='M14 8l-4 4 4 4' stroke='currentColor' fill='none' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>
        </svg>
    </button>
    `;
  }

  sPage += "</div>"; // end LogoWrapper

  // ✅ Right-side actions
  sPage += "<div class='NavActions'>";
  switch (currentPage) {
    case Page.LANDING:
      sPage += "<button class='NavButton login' onClick='LoginPage()'>Login</button>";
      sPage += "<button class='NavButton cta' onClick='SignupPage()'>Get Started</button>";
      break;
    case Page.LOGIN:
      sPage += "<button class='NavButton cta' onClick='SignupPage()'>Sign Up</button>";
      break;
    case Page.SIGNUP:
      sPage += "<button class='NavButton login' onClick='LoginPage()'>Login</button>";
      break;
    case Page.DASHBOARD:
//     case Page.AICHAT:
      sPage += "<div class='NavProfileCircle' onclick='UserProfilePage()'>JP</div>";
      break;
    default:
      break;
  }
  sPage += "</div>"; // end NavActions

  sPage += "</div>"; // end NavBar
  sPage += "</div>"; // end NavBarContainer
  return sPage;
};





const Hero = () => {
    let sPage = "";
    sPage += "<div class='HeroContainer'>";
    sPage += "<div class='HeroContent'>";
    sPage += "<h1 class='HeroTitle'>Plan Your UC Transfer With AI</h1>";
    sPage += "<p class='HeroSubtitle'>Smart advice based on your community college courses</p>";
    sPage += "<div id='HeroCTAWrapper'>";
    sPage += "<button class='HeroCTA' onClick='SignupPage()'>Get My Plan</button>";
    sPage += "</div>";
    sPage += "</div>";
    sPage += "</div>";
    return sPage;
};

const HowItWorks = () => {
    let sPage = "";
    sPage += "<div class='HowItWorksContainer'>";
    sPage += "<h2 class='HowItWorksTitle'>How It Works</h2>";
    sPage += "<div class='StepsWrapper'>";

    // Step 1
    sPage += "<div class='StepCard'>";
    sPage += "<div class='StepIcon'>🏫</div>";
    sPage += "<h3 class='StepTitle'>Choose Your College</h3>";
    sPage += "<p class='StepDescription'>Search for your California community college and start your transfer journey.</p>";
    sPage += "</div>";

    // Step 2
    sPage += "<div class='StepCard'>";
    sPage += "<div class='StepIcon'>📚</div>";
    sPage += "<h3 class='StepTitle'>Enter Your Courses</h3>";
    sPage += "<p class='StepDescription'>Tell us what you’ve taken — we’ll analyze your progress automatically.</p>";
    sPage += "</div>";

    // Step 3
    sPage += "<div class='StepCard'>";
    sPage += "<div class='StepIcon'>🎯</div>";
    sPage += "<h3 class='StepTitle'>Get a Transfer Plan</h3>";
    sPage += "<p class='StepDescription'>Receive personalized UC transfer advice instantly, powered by AI.</p>";
    sPage += "</div>";

    sPage += "</div>"; // end StepsWrapper
    sPage += "</div>"; // end HowItWorksContainer
    return sPage;
};

const ChatbotPreview = () => {
    let sPage = "";
    sPage += "<div class='ChatPreviewContainer'>";
    sPage += "<h2 class='ChatPreviewTitle'>Chat with Your AI Transfer Advisor</h2>";
    sPage += "<div class='ChatWindow'>";

    // User message
    sPage += "<div class='ChatMessage user'>";
    sPage += "<div class='ChatSender'>👤 You</div>";
    sPage += "<div class='ChatBubble'>What classes do I need to go to UCSD?</div>";
    sPage += "</div>";

    // AI response
    sPage += "<div class='ChatMessage ai'>";
    sPage += "<div class='ChatSender'>🤖 TransferAI</div>";
    sPage += "<div class='ChatBubble'>You’ll need to complete Math 1A, CSE 20, and Physics 4A. Great news — you’ve already finished Math 1A!</div>";
    sPage += "</div>";

    // Another user message
    sPage += "<div class='ChatMessage user'>";
    sPage += "<div class='ChatSender'>👤 You</div>";
    sPage += "<div class='ChatBubble'>Nice. Will those work for Computer Science?</div>";
    sPage += "</div>";

    // Message 4
    sPage += "<div class='ChatMessage ai'>";
    sPage += "<div class='ChatSender'>🤖 TransferAI</div>";
    sPage += "<div class='ChatBubble'>Yes! Those are part of the core lower-division prep for CS at UCSD.</div>";
    sPage += "</div>";

    // Message 5
    sPage += "<div class='ChatMessage user'>";
    sPage += "<div class='ChatSender'>👤 You</div>";
    sPage += "<div class='ChatBubble'>Cool. What else do I need to finish?</div>";
    sPage += "</div>";

    // Typing indicator
    sPage += "<div class='ChatMessage ai'>";
    sPage += "<div class='ChatSender'>🤖 TransferAI</div>";
    sPage += "<div class='ChatBubble typing'>";
    sPage += "<span class='dot'></span>";
    sPage += "<span class='dot'></span>";
    sPage += "<span class='dot'></span>";
    sPage += "</div>";
    sPage += "</div>";

    sPage += "</div>"; // close ChatWindow
    sPage += "</div>"; // close ChatPreviewContainer
    return sPage;
};

const StickyCTA = () => {
    let sPage = "";
    sPage += "<div class='StickyCTA'>";
    sPage += "<div class='StickyCTAInner'>";
    sPage += "<p class='StickyCTAText'>🎯 Ready to plan your UC transfer?</p>";
    sPage += "<button class='StickyCTAButton' onClick='SignupPage()'>Get My Plan</button>";
    sPage += "</div>";
    sPage += "</div>";
    return sPage;
};

window.addEventListener("scroll", () => {
    const heroCTA = document.getElementById("HeroCTAWrapper");
    const stickyCTA = document.querySelector(".StickyCTA");

    if (!heroCTA || !stickyCTA) return;

    const heroBottom = heroCTA.getBoundingClientRect().bottom;

    // If hero CTA is scrolled out of view
    if (heroBottom < 0) {
        stickyCTA.classList.add("show");
    } else {
        stickyCTA.classList.remove("show");
    }
});

const Footer = () => {
    let sPage = "";
    sPage += "<div class='FooterContainer'>";
    sPage += "<div class='FooterContent'>";

    // Left side: Logo
    sPage += "<div class='FooterLogo'>TransferAI</div>";

    // Right side: Nav links
    sPage += "<div class='FooterLinks'>";
    sPage += "<a href='#'>About</a>";
    sPage += "<a href='#'>Contact</a>";
    sPage += "<a href='#'>Privacy</a>";
    sPage += "<a href='https://github.com/' target='_blank'>GitHub</a>";
    sPage += "</div>";

    sPage += "</div>"; // FooterContent
    sPage += "<div class='FooterCopyright'>© 2025 TransferAI. All rights reserved.</div>";
    sPage += "</div>"; // FooterContainer
    return sPage;
};

// End Landing Page Stuff

// Login Page Stuff
const LoginPage = () => {
    let sPage = "";
    sPage += "<div class='MainContainer'>";
    sPage += NavBar(Page.LOGIN);

    sPage += "<div class='AuthCentered'>";

    sPage += "<div class='TitleWrapper'>"
    sPage += "<h2 class='AuthTitle LoginAuthTitle'>Log in to TransferAI</h2>";
    sPage += "</div>";

    sPage += "<div class='AuthForm'>";

    // Email input
    sPage += "<div class='FloatingGroup'>";
    sPage += "<input type='email' placeholder=' ' class='FloatingInput' id='emailInput' />";
    sPage += "<label for='emailInput' class='FloatingLabel'>Email address</label>";
    sPage += "</div>";

    // Password input
    sPage += "<div class='FloatingGroup'>";
    sPage += "<input type='password' placeholder=' ' class='FloatingInput' id='passwordInput' />";
    sPage += "<label for='passwordInput' class='FloatingLabel'>Password</label>";
    sPage += "</div>";

    sPage += "<a class='ForgotLink' href='#'>Forgot password?</a>";
    sPage += "<button class='AuthButton' onClick='checkLogin()'>Continue</button>";

    sPage += "</div>";


    sPage += "<p class='AuthRedirect'>Don’t have an account? <span class='AltLink' onclick='SignupPage()'>Sign up</span></p>";

    sPage += "<div class='AuthDivider'>";
    sPage += "<div class='Line'></div>";
    sPage += "<div class='OrText'>OR</div>";
    sPage += "<div class='Line'></div>";
    sPage += "</div>";

    sPage += "<button class='GoogleButton'>";
    sPage += "<img src='https://developers.google.com/identity/images/g-logo.png' class='GoogleIcon'>";
    sPage += "Continue with Google";
    sPage += "</button>";

    sPage += "</div>"; // end AuthCentered
    sPage += "</div>"; // end MainContainer

    document.getElementById('Body').innerHTML = sPage;
};

const checkLogin = () => {
    DashboardPage();
}
// End Login Page Stuff


// Sign up Page Stuff
const SignupPage = () => {
    let sPage = "";
    sPage += "<div class='MainContainer'>";
    sPage += NavBar(Page.SIGNUP);

    sPage += "<div class='AuthCentered'>";

    sPage += "<div class='TitleWrapper'>"
    sPage += "<h2 class='AuthTitle SignUpAuthTitle'>Sign Up For TransferAI</h2>";
    sPage += "</div>";

    sPage += "<div class='AuthForm'>";

    // Name input
    sPage += "<div class='FloatingGroup'>";
    sPage += "<input type='text' placeholder=' ' class='FloatingInput' id='nameInput' />";
    sPage += "<label for='nameInput' class='FloatingLabel'>Full name</label>";
    sPage += "</div>";

    // Email input
    sPage += "<div class='FloatingGroup'>";
    sPage += "<input type='email' placeholder=' ' class='FloatingInput' id='signupEmail' />";
    sPage += "<label for='signupEmail' class='FloatingLabel'>Email address</label>";
    sPage += "</div>";

    // Password input
    sPage += "<div class='FloatingGroup'>";
    sPage += "<input type='password' placeholder=' ' class='FloatingInput' id='signupPassword' />";
    sPage += "<label for='signupPassword' class='FloatingLabel'>Password</label>";
    sPage += "</div>";

    sPage += "<button class='AuthButton' onClick='checkNewAccount()'>Create Account</button>";
    sPage += "</div>"; // end AuthForm

    sPage += "<p class='AuthRedirect'>Already have an account? <span class='AltLink' onclick='LoginPage()'>Log in</span></p>";

    sPage += "<div class='AuthDivider'>";
    sPage += "<div class='Line'></div>";
    sPage += "<div class='OrText'>OR</div>";
    sPage += "<div class='Line'></div>";
    sPage += "</div>";

    sPage += "<button class='GoogleButton'>";
    sPage += "<img src='https://developers.google.com/identity/images/g-logo.png' class='GoogleIcon'>";
    sPage += "Sign up with Google";
    sPage += "</button>";

    sPage += "</div>"; // end AuthCentered
    sPage += "</div>"; // end MainContainer

    document.getElementById('Body').innerHTML = sPage;
};

const checkNewAccount = () => {
    DashboardPage();
}

// End sign up Page Stuff


// Dashboard Page Stuff
const DashboardPage = () => {
  let sPage = "";
  sPage += NavBar(Page.DASHBOARD);
  sPage += "<div class='MainContainer'>";

  sPage += "<div class='DashboardBody'>";

  sPage += "<div class='DashboardGreeting'>Hi Jake 👋 Ready to plan your transfer?</div>";

  // Hero Section: AI Chat
  sPage += "<div class='DashboardHeroCard'>";
  sPage += "<h2 class='DashboardHeroTitle'>AI Chat Advisor</h2>";
  sPage += "<p class='DashboardHeroSubtitle'>Ask anything about UC transfers. Your AI advisor is here 24/7.</p>";
  sPage += "<button class='DashboardHeroButton' onClick='AIChatPage()'>Open AI Chat</button>";
  sPage += "</div>";

  // Core Feature Grid (Only 3)
  sPage += "<div class='DashboardFeatureGrid'>";
  sPage += FeatureCard("Check Class Transferability", "See if your classes transfer to UCs", "ClassCheckerPage()");
  sPage += FeatureCard("Build Your Roadmap", "Create a semester-by-semester transfer plan", "RoadmapBuilderPage()");
//   sPage += FeatureCard("Saved Plans", "Access your saved class plans", "SavedPlansPage()");
  sPage += "</div>";

  sPage += "</div>"; // DashboardBody
  sPage += "</div>"; // MainContainer

  document.getElementById("Body").innerHTML = sPage;
};

const FeatureCard = (title, desc, onClick, isPro = false) => {
  return `
    <div class='FeatureCard' onclick='${onClick}'>
      <h3 class='FeatureCardTitle'>
        ${title}${isPro ? " <span class='ProBadge'>PRO</span>" : ""}
        <span class='HoverArrow'>&rarr;</span>
      </h3>
      <p class='FeatureCardDesc'>${desc}</p>
    </div>
  `;
};


// End Dashboard Page Stuff


const ClassCheckerPage = () => {
    let s = "<div class='MainContainer'>";
    s += NavBar(Page.DASHBOARD);
    s += "<div class='SimplePage'><h2>Class Checker Page</h2><p>Coming soon...</p></div>";
    s += "</div>";
    document.getElementById("Body").innerHTML = s;
};

const TransferPlanPage = () => {
    let s = "<div class='MainContainer'>";
    s += NavBar(Page.DASHBOARD);
    s += "<div class='SimplePage'><h2>My Transfer Plan</h2><p>Coming soon...</p></div>";
    s += "</div>";
    document.getElementById("Body").innerHTML = s;
};

const AIChatPage = () => {
  let sPage = "";

// ✅ Navbar stays outside
// sPage += NavBar(Page.AICHAT);

// ✅ Sidebar + main chat layout container
sPage += "<div class='MainContainer ChatLayout'>";
// ✅ Sidebar wrapper
sPage += "<div class='SidebarWrapper'>";

// 🔥 Logo + collapse section at the top
sPage += "<div class='SidebarHeader'>";
sPage += "  <div class='LogoAlignedWithSidebar'>";
sPage += "    <img id='SidebarLogo' class='LogoImageAISidebar clickable' src='logo.png' alt='TransferAI logo' onclick='DashboardPage()'>";
sPage += "    <button class='SidebarToggleButton NavCollapseButton' onclick='toggleSidebar()'>";
sPage += "      <svg class='ChevronIcon' xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'>";
sPage += "        <rect x='3' y='3' width='18' height='18' rx='6' ry='6' stroke='currentColor' fill='none' stroke-width='2'/>";
sPage += "        <path d='M14 8l-4 4 4 4' stroke='currentColor' fill='none' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>";
sPage += "      </svg>";
sPage += "    </button>";
sPage += "  </div>";
sPage += "</div>";

// ✅ Expanded Sidebar
sPage += "  <div class='ChatSidebar fadeInUp'>";

// Scrollable area
sPage += "    <div class='ChatHistoryListWrapper'>";
sPage += "      <div class='ChatSidebarHeader'>History</div>";
sPage += "      <div class='ChatHistoryList'>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(1)'>Transfer Plan Q&A</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(2)'>IGETC Planning</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(3)'>Class Equivalency</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(1)'>Transfer Plan Q&A</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(2)'>IGETC Planning</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(3)'>Class Equivalency</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(1)'>Transfer Plan Q&A</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(2)'>IGETC Planning</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(3)'>Class Equivalency</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(3)'>Class Equivalency</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(1)'>Transfer Plan Q&A</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(2)'>IGETC Planning</div>";
sPage += "        <div class='ChatHistoryItem' onclick='loadChatSession(3)'>Class Equivalency</div>";
sPage += "      </div>";
sPage += "    </div>"; // end .ChatHistoryListWrapper

// Profile (fixed at bottom)
sPage += "    <div class='SidebarProfileWrapper'>";
sPage += "      <div class='SidebarProfile'>";
sPage += "        <div class='SidebarProfileCircle'>JP</div>";
sPage += "        <div class='SidebarProfileText'>Free plan</div>";
sPage += "      </div>";
sPage += "      <svg class='SidebarProfileArrow' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>";
sPage += "        <path d='M6 15l6-6 6 6' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/>";
sPage += "      </svg>";
sPage += "    </div>"; // end .SidebarProfileWrapper

sPage += "  </div>"; // end .ChatSidebar

// ✅ Mini Sidebar for collapsed state
sPage += "<div class='MiniSidebar'>";

// ⬆️ Top logo
sPage += "  <img class='MiniSidebarLogo clickable' src='logo_hat.png' alt='Logo' onclick='DashboardPage()'>";

// ▶️ Expand button
sPage += "  <button class='SidebarToggleButton' onclick='toggleSidebar()'>";
sPage += "    <svg class='ChevronIconMini' xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'>";
sPage += "      <rect x='3' y='3' width='18' height='18' rx='6' ry='6' stroke='currentColor' fill='none' stroke-width='2'/>";
sPage += "      <path class='ChevronMiniPath' d='M10 8l4 4-4 4' stroke='currentColor' fill='none' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>";
sPage += "    </svg>";
sPage += "  </button>";

// ➕ New chat button
// sPage += "  <button class='NewChatButton' onclick='createNewChat()'>";
// sPage += "    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='20' height='20'>";
// sPage += "      <path fill='currentColor' d='M12 5v14m-7-7h14'/>";
// sPage += "    </svg>";
// sPage += "  </button>";

sPage += "</div>"; // end .MiniSidebar

// 👤 Collapsed Profile Circle at bottom
sPage += "<div class='SidebarProfileMiniWrapper'>";
sPage += "  <div class='SidebarProfileMini'>";
sPage += "    <div class='SidebarProfileCircle'>JP</div>";
sPage += "  </div>";
sPage += "</div>";




sPage += "</div>"; // end .SidebarWrapper



  // ✅ Floating Chat Main Area
  sPage += "<div class='AIChatPageBody'>";

  // 🆕 New polished greeting block
  sPage += "<div class='AIChatGreetingWrapper fadeInUp'>";
  sPage += "  <div class='AIChatGreeting'>";
  sPage += "    <div class='AIChatGreetingRow'>";
  sPage += "      <span class='wave'>👋</span>";
  sPage += "      <div class='greeting-text'>";
  sPage += "        <div class='greeting-title'>Welcome back, Jake!</div>";
  sPage += "        <div class='greeting-subtext'>Your personalized UC transfer assistant is here to help.</div>";
  sPage += "      </div>";
  sPage += "    </div>";
  sPage += "  </div>";
  sPage += "</div>";

  // Chat history
  sPage += "<div class='ChatHistory' id='ChatHistory'>";
  sPage += "<!-- Chat bubbles will append here -->";
  sPage += "</div>";

sPage += "<div class='ChatInputContainer sticky-footer'>";
sPage += "  <div class='ChatInputLayout'>";
sPage += "    <textarea id='ChatInput' class='ChatInput' placeholder='Type your question...'></textarea>";
sPage += "    <button class='SendIconButton' onClick='sendChatMessage()' disabled>";
sPage += "      <svg class='SendIcon' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>";
sPage += "        <path fill='white' d='M7 14l5-5 5 5H7z' />";
sPage += "      </svg>";
sPage += "    </button>";
sPage += "  </div>";
sPage += "</div>";




  // ⚠️ Footer Warning
  sPage += "<div class='ChatDisclaimer'>TransferAI can make mistakes. Check important info.</div>";

  sPage += "</div></div>"; // Close AIChatPageBody + ChatLayout
  document.getElementById("Body").innerHTML = sPage;

  // ✅ Force sidebar expanded on load
  document.querySelector('.ChatSidebar')?.classList.remove('collapsed');
  document.body.classList.remove('sidebar-collapsed');

  // ✅ Ensure correct logo for expanded state
  document.getElementById('SidebarLogo')?.setAttribute('src', 'logo.png');

  // Get references to the input and send button elements
  const input = document.getElementById("ChatInput");
  input.focus();
  const sendBtn = document.querySelector(".SendIconButton");

// Function to update the height of the input field dynamically
    function adjustInputHeight() {
    const input = document.getElementById("ChatInput");

    // Reset to one-line height for recalculation
    input.style.height = '24px'; // ← Matches initial CSS height

    // Calculate desired height (up to max)
    const maxHeight = 160;
    const newHeight = Math.min(input.scrollHeight, maxHeight);

    input.style.height = `${newHeight}px`;
    }

  // Function to update send button state (optional, but useful for enabling/disabling the button)
  function updateSendButtonState() {
    const sText = input.value.trim();
    // Enable the button if the input is not empty, otherwise disable
    if (sText.length > 0) {
      sendBtn.disabled = false;
    } else {
      sendBtn.disabled = true;
    }
  }

  // Listen for input events to dynamically adjust height and send button state
  input.addEventListener('input', function() {
    adjustInputHeight(); // Adjust height as text is entered
    updateSendButtonState(); // Update send button state
  });

  // Listen for Enter key (for sending) and Shift + Enter (for multiline input)
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Shift + Enter: Add a new line
        return;
      } else {
        // Enter (without Shift): Send the message
        e.preventDefault(); // Prevent adding a new line
        sendChatMessage(); // Call your send message function here
      }
    }
  });

  // Call adjustInputHeight initially to set the correct height when the page loads
  adjustInputHeight();
};

function toggleSidebar() {
  const sidebar = document.querySelector('.ChatSidebar');
  const body = document.body;
  const logo = document.getElementById('SidebarLogo');
  const chevronPath = document.querySelector('.ChevronMiniPath');

  // Toggle class for collapsed state
  sidebar.classList.toggle('collapsed');
  body.classList.toggle('sidebar-collapsed');

  // 1️⃣ Change logo source
  if (sidebar.classList.contains('collapsed')) {
    logo.src = 'logo_hat.png'; // collapsed state
  } else {
    logo.src = 'logo.png'; // expanded state
  }

  // 2️⃣ Flip chevron arrow
  if (chevronPath) {
    if (sidebar.classList.contains('collapsed')) {
      chevronPath.setAttribute('d', 'M10 8l4 4-4 4'); // ▶
    } else {
      chevronPath.setAttribute('d', 'M14 8l-4 4 4 4'); // ◀
    }
  }
}






// Define sendChatMessage function
function sendChatMessage() {
  const input = document.getElementById("ChatInput");
  const message = input.value.trim();

  if (message) {
    const userBubble = appendChatBubble(message, 'user');
    input.value = "";

    const greetingEl = document.querySelector('.AIChatGreetingWrapper');
    const chatBody = document.querySelector('.AIChatPageBody');

    if (greetingEl && !greetingEl.classList.contains('dismissed')) {
      // Step 1: Add .dismissed to trigger fade
      greetingEl.classList.add('dismissed'); // Starts the fade-out animation for the greeting

      // Step 2: Wait for the fade-out, then adjust layout
      setTimeout(() => {
        greetingEl.style.maxHeight = '0'; // Smoothly collapse greeting height
        greetingEl.style.marginBottom = '0'; // Remove space below
        greetingEl.style.padding = '0'; // Collapse padding
        userBubble.classList.remove('pulse'); // Stop the pulse animation
        chatBody.classList.add('compact-mode'); // Adjust the layout for subsequent messages
      }, 700); // Match the fade-out duration

    }

    // AI bubble delay
    setTimeout(() => {
      const aiBubble = appendChatBubble("That's a great question! Let me check that for you.", 'ai');

      // Apply float-up effect to the AI bubble
      aiBubble.classList.add('floatUp');
    }, 1500); // Allow first message to complete its pulse effect before AI response
  }
}

// Helper function to append chat bubbles
function appendChatBubble(text, sender) {
  const container = document.getElementById("ChatHistory");
  const bubble = document.createElement("div");

  // Add pulse animation class for user messages
  bubble.className =
    sender === 'user'
      ? 'ChatMessageBubble ChatMessageUser pulse' // Add "pulse" class here for user message
      : 'ChatMessageBubble ChatMessageAI floatUp';

  bubble.innerHTML = `
    <div class="BubbleContent">${text}</div>
    <div class="BubbleMeta">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
  `;

  container.appendChild(bubble);
  bubble.scrollIntoView({ behavior: "smooth", block: "end" });

  return bubble;
}







function loadChatSession(sessionId) {
  alert('Loading session #' + sessionId);
}


