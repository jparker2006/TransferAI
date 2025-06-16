/* Sidebar renderer for TransferAI */

/**
 * Build and return HTML string for the left sidebar.
 * @returns {string}
 */
export function renderSidebar() {
    const navItems = [
        { icon: 'fas fa-th-large', label: 'Dashboard' },
        { icon: 'fas fa-comments', label: 'Chat' },
        { icon: 'fas fa-calendar-alt', label: 'Schedule Builder' },
        { icon: 'fas fa-route', label: 'Transfer Planner' },
        { icon: 'fas fa-percentage', label: 'Transfer Odds' },
        { icon: 'fas fa-clipboard-check', label: 'Audit' },
        { icon: 'fas fa-cog', label: 'Settings' }
    ];

    let sSidebar = '';
    sSidebar += "<div class='SidebarWrapper'>";

    // Header with logo and collapse
    sSidebar += "  <div class='SidebarHeader'>";
    sSidebar += "      <img src='assets/logo_hat.png' alt='TransferAI Logo' class='LogoImage'/>";
    sSidebar += "      <i class='fas fa-angle-double-left CollapseBtn' id='CollapseBtn'></i>";
    sSidebar += "  </div>";

    // Navigation
    sSidebar += "  <ul class='NavList'>";
    navItems.forEach(item => {
        sSidebar += `    <li class='NavItem'><i class='${item.icon}'></i><span class='NavLabel'>${item.label}</span></li>`;
    });
    sSidebar += "  </ul>";

    // Footer profile
    sSidebar += "  <div class='SidebarFooter'>";
    sSidebar += "    <div class='ProfileCircle'>JP</div>";
    sSidebar += "    <div class='PlanLabel'>Free Plan</div>";
    sSidebar += "  </div>";

    sSidebar += "</div>";

    return sSidebar;
}

// Attach collapse listener after DOM load
export function setupSidebarInteractions() {
    const btn = document.getElementById('CollapseBtn');
    if (!btn) return;
    btn.addEventListener('click', () => {
        document.body.classList.toggle('sidebar-collapsed');
    });
} 