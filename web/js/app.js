/**
 * YouthFit AI - Global Application Utilities
 */

// Smooth scroll for in-page anchors
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href').substring(1);
      if (!targetId) return;
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        e.preventDefault();
        targetEl.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
});

/**
 * Toast Notification Utility
 */
function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('youthfit-toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'youthfit-toast-container';
    toastContainer.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
    `;
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  const bg = type === 'success' ? '#006c4a' : type === 'error' ? '#ba1a1a' : '#004ac6';
  toast.style.cssText = `
    background: ${bg};
    color: #ffffff;
    padding: 12px 20px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.25s ease-out;
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 8px;
  `;
  toast.innerHTML = `
    <span class="material-symbols-outlined text-[18px]">
      ${type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info'}
    </span>
    <span>${message}</span>
  `;

  toastContainer.appendChild(toast);
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

/**
 * Toggle Hot Policies Section (Expand / Collapse)
 */
function toggleHotPolicies() {
  const cards = document.getElementById('hot-policies-grid');
  const banner = document.getElementById('expanded-status-banner');
  const icon = document.getElementById('policy-toggle-icon');
  const txt = document.getElementById('policy-toggle-text');
  if (!cards) return;

  const isHidden = cards.classList.contains('hidden');
  if (isHidden) {
    cards.classList.remove('hidden');
    if (banner) banner.classList.remove('hidden');
    if (icon) icon.textContent = 'expand_less';
    if (txt) txt.textContent = '주요 정책 목록 접기';
  } else {
    cards.classList.add('hidden');
    if (banner) banner.classList.add('hidden');
    if (icon) icon.textContent = 'expand_more';
    if (txt) txt.textContent = '주요 정책 목록 펼치기';
  }
}

/**
 * Theme Management (Light: Fintech Civic <-> Dark: Kinetic Glass AI)
 */
function initTheme() {
  const savedTheme = localStorage.getItem('youthfit_theme');
  const isDark = savedTheme === 'dark';
  applyTheme(isDark);
}

function applyTheme(isDark) {
  if (isDark) {
    document.documentElement.classList.add('dark');
    document.body && document.body.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
    document.body && document.body.classList.remove('dark');
  }

  // Update theme icons and labels
  document.querySelectorAll('.theme-icon').forEach(icon => {
    icon.textContent = isDark ? 'light_mode' : 'dark_mode';
  });
  document.querySelectorAll('#theme-toggle-label, .theme-toggle-label').forEach(label => {
    label.textContent = isDark ? '라이트 모드' : '다크 모드';
  });
}

function toggleTheme() {
  const isDark = document.documentElement.classList.contains('dark');
  const nextDark = !isDark;
  applyTheme(nextDark);
  localStorage.setItem('youthfit_theme', nextDark ? 'dark' : 'light');
  
  const msg = nextDark ? '다크 모드 (Kinetic Glass AI)로 전환되었습니다.' : '라이트 모드 (Fintech Civic)로 전환되었습니다.';
  showToast(msg, 'info');
}

// Initialize theme immediately
initTheme();
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});

window.showToast = showToast;
window.toggleHotPolicies = toggleHotPolicies;
window.initTheme = initTheme;
window.toggleTheme = toggleTheme;


/**
 * Centralized Auth Session Lifecycle Manager
 * 
 * Policy:
 * 1. Default active session: stored strictly in sessionStorage (retained across F5/refresh and page navigation, automatically destroyed when the browser window/tab closes).
 * 2. Remember-me ("이 기기에서 로그인 상태 유지"): stored in localStorage with an explicit 7-day expiration timestamp (remember_expires).
 * 3. Landing page clean state: If a user closes and re-opens the browser without remember-me, or visits for the first time, they are always in a clean logged-out state (no lingering credentials).
 */
const SESSION_VERSION_KEY = 'youthfit_session_ver';
const CURRENT_SESSION_VERSION = '20260918_v3';

function getAuthUser() {
  try {
    // 1. Validate active session storage (retained on refresh, destroyed on tab/window close)
    const sessionVer = sessionStorage.getItem(SESSION_VERSION_KEY);
    const sessionRaw = sessionStorage.getItem('youthfit_user');
    if (sessionRaw && sessionVer === CURRENT_SESSION_VERSION) {
      return JSON.parse(sessionRaw);
    }

    // 2. Check persistent localStorage ONLY if explicitly remembered and not expired
    const localRaw = localStorage.getItem('youthfit_user');
    if (localRaw) {
      const user = JSON.parse(localRaw);
      // Expired: completely purge
      if (user && user.remember_expires && Date.now() > user.remember_expires) {
        localStorage.removeItem('youthfit_user');
        localStorage.removeItem('youthfit_member_profile');
        localStorage.removeItem('youthfit_diagnosis_result');
        return null;
      }
      // Valid remember-me session: hydrate sessionStorage for current active session
      if (user && user.remember_expires && Date.now() <= user.remember_expires) {
        sessionStorage.setItem('youthfit_user', localRaw);
        sessionStorage.setItem(SESSION_VERSION_KEY, CURRENT_SESSION_VERSION);
        return user;
      }
      // Legacy user without explicit remember_expires: purge completely so landing page is logged out!
      localStorage.removeItem('youthfit_user');
      localStorage.removeItem('youthfit_member_profile');
      localStorage.removeItem('youthfit_diagnosis_result');
      return null;
    }
  } catch (e) {
    console.error("Auth session parse error:", e);
  }
  return null;
}

function setAuthUser(userData, remember = false) {
  if (!userData) return;
  const userStr = JSON.stringify(userData);
  sessionStorage.setItem(SESSION_VERSION_KEY, CURRENT_SESSION_VERSION);
  sessionStorage.setItem('youthfit_user', userStr);

  if (remember) {
    const clone = Object.assign({}, userData);
    clone.remember_expires = Date.now() + 7 * 24 * 60 * 60 * 1000; // 7 days
    localStorage.setItem('youthfit_user', JSON.stringify(clone));
  } else {
    // When remember is false, purge any residual localStorage
    localStorage.removeItem('youthfit_user');
    localStorage.removeItem('youthfit_member_profile');
    localStorage.removeItem('youthfit_diagnosis_result');
  }
}

function clearAuthUser() {
  sessionStorage.removeItem(SESSION_VERSION_KEY);
  sessionStorage.removeItem('youthfit_user');
  sessionStorage.removeItem('youthfit_member_profile');
  sessionStorage.removeItem('youthfit_diagnosis_result');
  sessionStorage.removeItem('youthfit_transient_diagnosis_result');
  sessionStorage.removeItem('youthfit_transient_profile');
  sessionStorage.clear();

  localStorage.removeItem('youthfit_user');
  localStorage.removeItem('youthfit_member_profile');
  localStorage.removeItem('youthfit_diagnosis_result');
  localStorage.removeItem('youthfit_profile');
}

window.getAuthUser = getAuthUser;
window.setAuthUser = setAuthUser;
window.clearAuthUser = clearAuthUser;

// Immediate Cleanup of any stale/legacy unremembered credentials so landing is 100% clean
(function purgeLegacyAuthResidue() {
  try {
    const sessionVer = sessionStorage.getItem(SESSION_VERSION_KEY);
    if (sessionVer !== CURRENT_SESSION_VERSION) {
      sessionStorage.removeItem('youthfit_user');
      sessionStorage.removeItem('youthfit_member_profile');
      sessionStorage.removeItem('youthfit_diagnosis_result');
    }
    const legacyLocal = localStorage.getItem('youthfit_user');
    if (legacyLocal) {
      const parsed = JSON.parse(legacyLocal);
      if (!parsed || !parsed.remember_expires || Date.now() > parsed.remember_expires) {
        localStorage.removeItem('youthfit_user');
        localStorage.removeItem('youthfit_member_profile');
        localStorage.removeItem('youthfit_diagnosis_result');
      }
    }
  } catch (e) {
    localStorage.removeItem('youthfit_user');
  }
})();

/**
 * Global Auth Status Synchronization across all web pages
 */
function updateGlobalAuthHeader() {
  try {
    const user = getAuthUser();
    const adminLink = document.getElementById('sidebar-admin-link');
    if (!user) {
      if (adminLink) {
        adminLink.classList.add('hidden');
        adminLink.style.display = 'none';
      }
      return;
    }

    // Admin privileges check for sidebar admin monitoring button
    if (adminLink) {
      const uRole = (user.role || '').toLowerCase();
      const uEmail = (user.email || '').toLowerCase();
      const isAdmin = uRole === 'admin' || uEmail === 'admin@youthfit.kr' || uEmail.startsWith('admin@') || uEmail === 'admin';
      if (isAdmin) {
        adminLink.classList.remove('hidden');
        adminLink.style.display = 'flex';
      } else {
        adminLink.classList.add('hidden');
        adminLink.style.display = 'none';
      }
    }

    if (!user.name) return;

    // If badge already exists, update name and title directly
    const existingBadge = document.getElementById('header-user-badge-link');
    if (existingBadge) {
      existingBadge.innerHTML = `
        <span class="material-symbols-outlined text-[15px]">account_circle</span>
        <span>${user.name} 님</span>
      `;
      existingBadge.title = `${user.name} (${user.email}) - 프로필 및 계정 설정`;
    }

    // 1. Replace login text links with Member Profile Badge
    const authLinks = document.querySelectorAll('a[href="auth.html"], a[href="auth"]');
    authLinks.forEach(link => {
      if (link.textContent.trim() === "로그인") {
        const container = document.createElement('div');
        container.className = 'flex items-center gap-2 text-xs font-semibold';
        container.innerHTML = `
          <a id="header-user-badge-link" href="profile.html" class="px-2.5 py-1 rounded-full bg-primary-fixed text-primary flex items-center gap-1 font-bold hover:bg-primary-fixed-dim transition-colors shadow-sm" title="${user.name} (${user.email}) - 프로필 및 계정 설정">
            <span class="material-symbols-outlined text-[15px]">account_circle</span>
            <span>${user.name} 님</span>
          </a>
          <button type="button" class="text-xs text-outline hover:text-error hover:underline cursor-pointer" onclick="handleGlobalLogout()">
            로그아웃
          </button>
        `;
        link.replaceWith(container);
      } else if (link.querySelector('.material-symbols-outlined')?.textContent.trim() === "person") {
        link.title = `${user.name} (${user.email}) - 프로필 및 계정 설정`;
        link.href = 'profile.html';
        link.classList.add('ring-2', 'ring-primary', 'ring-offset-1');
      }
    });

    // 2. Change "비회원 진단" button to "내 진단 대시보드" in header
    const guestLinks = document.querySelectorAll('header a');
    guestLinks.forEach(a => {
      if (a.textContent.includes('비회원 진단')) {
        a.href = 'dashboard.html';
        a.className = 'hidden md:inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-primary bg-primary-fixed/60 hover:bg-primary-fixed rounded-lg transition-colors border border-primary/20 shadow-sm';
        a.innerHTML = `
          <span class="material-symbols-outlined text-[16px] text-primary">dashboard</span>
          <span>내 진단 대시보드</span>
        `;
      }
    });
  } catch (e) {
    console.error("Auth header sync error:", e);
  }
}

/**
 * Requirement 3: Personalized Hero Experience for Logged-in Members
 * Replaces the static 김OO example with the user's personal profile & 1-click diagnosis.
 */
function renderPersonalizedHero() {
  const container = document.getElementById('hero-persona-card-container');
  if (!container) return;

  const user = getAuthUser();
  if (!user || !user.name) return; // Keep the default '김OO 님 (가상 예시)' card for guests

  try {
    // Retrieve user's conditions (or default fallback)
    const savedProf = localStorage.getItem('youthfit_member_profile');
    const userProf = user.profile?.user_conditions || (savedProf ? JSON.parse(savedProf) : null);
    
    const profile = userProf || {
      age: 24,
      region: '서울',
      regionFull: '서울특별시',
      district: '관악구',
      jobStatus: 'jobseeker',
      household: 'single',
      income: 'income60'
    };

    const jobMap = {
      jobseeker: '취업준비생',
      employed: '재직자(중소·스타트업)',
      freelancer: '프리랜서·창업가',
      student: '대학(원)생'
    };
    const householdMap = {
      single: '1인 단독가구',
      multi: '다인가구(동거)'
    };
    const incomeMap = {
      income60: '기준 중위소득 60% 이하',
      income120: '중위소득 60%~120%',
      income150: '중위소득 120%~150%',
      incomeOver: '중위소득 150% 초과'
    };

    const jobLabel = jobMap[profile.jobStatus] || '청년 구직자';
    const houseLabel = householdMap[profile.household] || '1인 가구';
    const regionLabel = `${profile.regionFull || profile.region || '서울'} ${profile.district || ''}`.trim();
    const incomeLabel = incomeMap[profile.income] || '소득 60% 이하';

    // Recent diagnosis summary
    const recent = user.profile?.recent_diagnosis;
    const hasRecent = !!recent;
    const benefitAmountStr = hasRecent ? (recent.total_benefit_formatted || Number(recent.total_benefit || 3200000).toLocaleString('ko-KR')) : '3,200,000';
    const matchCount = hasRecent ? (recent.matched_count || 4) : 4;

    container.innerHTML = `
      <div class="absolute -inset-1 rounded-3xl bg-gradient-to-r from-primary/30 to-secondary/30 opacity-60 blur-xl"></div>
      <div class="relative flex flex-col rounded-3xl bg-surface-container-lowest p-space-lg shadow-xl border-2 border-primary/25">
        
        <!-- Member Header -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-space-sm">
            <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-container text-on-primary shadow-md font-extrabold text-lg">
              ${user.name.charAt(0)}
            </div>
            <div>
              <div class="flex items-center gap-1.5">
                <span class="font-bold text-base text-on-surface">${user.name} 님</span>
                <span class="rounded-full bg-secondary-fixed/70 px-2 py-0.5 text-xs font-bold text-secondary flex items-center gap-0.5">
                  <span class="material-symbols-outlined text-xs">verified</span> 정식회원
                </span>
              </div>
              <p class="text-xs text-on-surface-variant">${user.email}</p>
            </div>
          </div>
          <span class="rounded-full bg-primary-fixed/60 text-primary px-3 py-1 text-xs font-bold flex items-center gap-1">
            <span class="material-symbols-outlined text-[14px]">auto_awesome</span> 맞춤 프로필
          </span>
        </div>

        <!-- Saved Conditions Summary -->
        <div class="mt-space-md rounded-2xl bg-surface-container-low p-3.5 border border-hairline-border space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-on-surface flex items-center gap-1">
              <span class="material-symbols-outlined text-sm text-primary">person_pin</span>
              <span>나의 등록 진단 조건</span>
            </span>
            <a href="diagnosis.html" class="text-xs text-primary font-semibold hover:underline flex items-center gap-0.5">
              <span>조건 수정</span>
              <span class="material-symbols-outlined text-xs">tune</span>
            </a>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="bg-surface-container-lowest p-2.5 rounded-xl border border-hairline-border space-y-0.5">
              <span class="text-outline text-[11px] block">연령 및 거주지</span>
              <span class="font-bold text-on-surface truncate block">만 ${profile.age}세 · ${regionLabel}</span>
            </div>
            <div class="bg-surface-container-lowest p-2.5 rounded-xl border border-hairline-border space-y-0.5">
              <span class="text-outline text-[11px] block">경제활동 및 가구</span>
              <span class="font-bold text-on-surface truncate block">${jobLabel} · ${houseLabel}</span>
            </div>
          </div>
        </div>

        <!-- Benefit Preview Box -->
        <div class="mt-3 rounded-2xl bg-gradient-to-br from-primary-fixed/20 via-surface-container-low to-secondary-fixed/20 p-4 border border-primary/20">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-on-surface-variant">
              ${hasRecent ? '최근 진단 수혜 분석 결과' : '2026 예상 청년 지원금'}
            </span>
            <span class="inline-flex items-center gap-1 rounded-md bg-secondary-container px-2 py-0.5 text-xs font-bold text-on-secondary-container">
              <span class="material-symbols-outlined text-[13px]">check_circle</span>
              ${matchCount}건 적격 판별
            </span>
          </div>
          <div class="mt-1 flex items-baseline gap-1.5">
            <span class="text-sm font-semibold text-on-surface">연 약</span>
            <span class="font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-secondary">${benefitAmountStr}</span>
            <span class="text-base font-bold text-on-surface">원</span>
          </div>
          <p class="mt-1 text-xs text-on-surface-variant">
            ${regionLabel} 기준 청년 맞춤 복지·주거·일자리 지원금
          </p>
        </div>

        <!-- 1-Click Rapid Diagnosis CTA Button -->
        <div class="mt-space-md space-y-2">
          <button id="btn-one-click" onclick="triggerOneClickDiagnosis()" class="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-primary to-primary-container text-on-primary font-bold text-sm shadow-md hover:shadow-lg hover:brightness-105 active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer">
            <span class="material-symbols-outlined text-xl text-secondary">bolt</span>
            <span>내 조건으로 원클릭 즉시 진단</span>
            <span class="material-symbols-outlined text-base">arrow_forward</span>
          </button>
          
          <div class="flex items-center justify-between px-1 text-xs text-on-surface-variant pt-1">
            <span class="flex items-center gap-1">
              <span class="material-symbols-outlined text-[14px] text-secondary">flash_on</span>
              <span>재설문 없이 0.5초 즉시 매칭</span>
            </span>
            <a href="diagnosis.html" class="text-primary hover:underline font-semibold flex items-center gap-0.5">
              <span>조건 변경 진단</span>
              <span class="material-symbols-outlined text-xs">edit_note</span>
            </a>
          </div>
        </div>

        ${hasRecent ? `
          <div class="mt-3 pt-2.5 border-t border-hairline-border flex items-center justify-between text-xs">
            <span class="text-outline">최근 진단일: ${recent.date || '최근'}</span>
            <a href="dashboard.html" class="font-bold text-primary hover:underline flex items-center gap-0.5">
              <span>결과 보관함 바로가기</span>
              <span class="material-symbols-outlined text-xs">arrow_outward</span>
            </a>
          </div>
        ` : ''}

      </div>
    `;

    // Item 8: For logged-in users, update the left Hero CTA to point directly to dashboard & re-diagnosis
    const guestCtaBox = document.getElementById('hero-guest-cta-box');
    if (guestCtaBox) {
      guestCtaBox.innerHTML = `
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <a href="dashboard.html" class="group flex items-center justify-center gap-2 px-7 py-4 rounded-2xl bg-primary text-on-primary font-bold text-base shadow-lg shadow-primary/25 hover:bg-primary-container hover:shadow-primary/40 transition-all active:scale-[0.98] cursor-pointer">
            <span class="material-symbols-outlined text-xl">dashboard</span>
            <span>나의 맞춤 대시보드 바로가기</span>
            <span class="material-symbols-outlined text-lg transition-transform group-hover:translate-x-1">arrow_forward</span>
          </a>
          <a href="diagnosis.html" class="inline-flex items-center justify-center gap-2 px-5 py-4 rounded-2xl bg-surface-container text-on-surface font-semibold text-sm hover:bg-surface-container-high transition-colors border border-hairline-border cursor-pointer">
            <span class="material-symbols-outlined text-lg text-primary">replay</span>
            <span>새로운 조건으로 다시 진단</span>
          </a>
        </div>
      `;
    }
  } catch (e) {
    console.error("Personalized hero render failed:", e);
  }
}

/**
 * 1-Click Rapid Diagnosis for Logged-in Members
 */
async function triggerOneClickDiagnosis() {
  const btn = document.getElementById('btn-one-click');
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <span class="material-symbols-outlined text-lg animate-spin">progress_activity</span>
      <span>AI 706건 정책 실시간 매칭 중...</span>
    `;
  }

  try {
    const user = getAuthUser();
    
    // Retrieve member profile
    const savedProf = sessionStorage.getItem('youthfit_member_profile') || localStorage.getItem('youthfit_member_profile');
    const profile = (user && user.profile?.user_conditions) || (savedProf ? JSON.parse(savedProf) : {
      age: 24,
      region: '서울',
      regionFull: '서울특별시',
      district: '관악구',
      jobStatus: 'jobseeker',
      household: 'single',
      income: 'income60'
    });

    // Run Diagnosis API
    const res = await fetch('/api/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    });

    const json = await res.json();
    if (!res.ok || json.status !== 'success') {
      throw new Error(json.detail || '진단 연산에 실패했습니다.');
    }

    const diagData = json.data;
    sessionStorage.setItem('youthfit_diagnosis_result', JSON.stringify(diagData));
    sessionStorage.setItem('youthfit_member_profile', JSON.stringify(profile));
    if (localStorage.getItem('youthfit_user')) {
      localStorage.setItem('youthfit_diagnosis_result', JSON.stringify(diagData));
      localStorage.setItem('youthfit_member_profile', JSON.stringify(profile));
    }

    // Persist to user DB if user exists
    if (user && user.id) {
      fetch('/api/user/save-diagnosis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          profile: profile,
          diagnosis_result: diagData
        })
      }).catch(e => console.warn("DB save sync error:", e));

      // Also update local user object
      user.profile = user.profile || {};
      user.profile.user_conditions = profile;
      user.profile.recent_diagnosis = {
        date: new Date().toISOString().slice(0, 19).replace('T', ' '),
        profile: profile,
        total_benefit: diagData.total_benefit,
        total_benefit_formatted: diagData.total_benefit_formatted,
        matched_count: diagData.matched_count
      };
      sessionStorage.setItem('youthfit_user', JSON.stringify(user));
      if (localStorage.getItem('youthfit_user')) {
        localStorage.setItem('youthfit_user', JSON.stringify(user));
      }
    }

    if (window.showToast) {
      window.showToast('✓ 맞춤 진단 완료! 대시보드로 이동합니다.', 'success');
    }

    setTimeout(() => {
      window.location.href = 'dashboard.html';
    }, 400);

  } catch (err) {
    alert("원클릭 진단 오류: " + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

function handleGlobalLogout() {
  clearAuthUser();

  if (window.showToast) {
    window.showToast('성공적으로 로그아웃되었습니다.', 'info');
  } else {
    alert('로그아웃되었습니다.');
  }
  setTimeout(() => {
    window.location.reload();
  }, 400);
}

window.triggerOneClickDiagnosis = triggerOneClickDiagnosis;
window.handleGlobalLogout = handleGlobalLogout;

document.addEventListener('DOMContentLoaded', () => {
  updateGlobalAuthHeader();
  renderPersonalizedHero();
});


