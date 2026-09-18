/**
 * YouthFit AI - Authentication & Google OAuth Logic with Database Persistence
 */

// Fallback Auth Helpers in case app.js loads asynchronously or is missing
function clearAuthUser() {
  if (typeof window.clearAuthUser === 'function' && window.clearAuthUser !== clearAuthUser) {
    return window.clearAuthUser();
  }
  try {
    sessionStorage.clear();
    localStorage.removeItem('youthfit_user');
    localStorage.removeItem('youthfit_member_profile');
    localStorage.removeItem('youthfit_diagnosis_result');
    localStorage.removeItem('youthfit_profile');
  } catch (e) {
    console.warn("clearAuthUser fallback error:", e);
  }
}

function setAuthUser(userData, remember = false) {
  if (typeof window.setAuthUser === 'function' && window.setAuthUser !== setAuthUser) {
    return window.setAuthUser(userData, remember);
  }
  try {
    if (!userData) return;
    sessionStorage.setItem('youthfit_session_ver', '20260918_v3');
    sessionStorage.setItem('youthfit_user', JSON.stringify(userData));
    if (remember) {
      const clone = Object.assign({}, userData);
      clone.remember_expires = Date.now() + 7 * 24 * 60 * 60 * 1000;
      localStorage.setItem('youthfit_user', JSON.stringify(clone));
    } else {
      localStorage.removeItem('youthfit_user');
      localStorage.removeItem('youthfit_member_profile');
      localStorage.removeItem('youthfit_diagnosis_result');
    }
  } catch (e) {
    console.warn("setAuthUser fallback error:", e);
  }
}

// Tab Switching (Login / Signup / Guest)
function switchAuthTab(tab) {
  const paneLogin = document.getElementById('pane-login');
  const paneSignup = document.getElementById('pane-signup');
  const paneGuest = document.getElementById('pane-guest');
  
  const tabLogin = document.getElementById('tab-login');
  const tabSignup = document.getElementById('tab-signup');
  const tabGuest = document.getElementById('tab-guest');

  // Reset all panes
  [paneLogin, paneSignup, paneGuest].forEach(p => p && p.classList.add('hidden'));
  [tabLogin, tabSignup, tabGuest].forEach(t => {
    if (t) {
      t.classList.remove('bg-surface-container-lowest', 'text-primary', 'shadow-sm');
      t.classList.add('text-on-surface-variant');
    }
  });

  if (tab === 'login') {
    if (paneLogin) paneLogin.classList.remove('hidden');
    if (tabLogin) {
      tabLogin.classList.add('bg-surface-container-lowest', 'text-primary', 'shadow-sm');
      tabLogin.classList.remove('text-on-surface-variant');
    }
  } else if (tab === 'signup') {
    if (paneSignup) paneSignup.classList.remove('hidden');
    if (tabSignup) {
      tabSignup.classList.add('bg-surface-container-lowest', 'text-primary', 'shadow-sm');
      tabSignup.classList.remove('text-on-surface-variant');
    }
  } else if (tab === 'guest') {
    if (paneGuest) paneGuest.classList.remove('hidden');
    if (tabGuest) {
      tabGuest.classList.add('bg-surface-container-lowest', 'text-primary', 'shadow-sm');
      tabGuest.classList.remove('text-on-surface-variant');
    }
  }
}

// Password toggle helper
function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const icon = btn.querySelector('.material-symbols-outlined');
  if (input.type === 'password') {
    input.type = 'text';
    if (icon) icon.textContent = 'visibility_off';
  } else {
    input.type = 'password';
    if (icon) icon.textContent = 'visibility';
  }
}

// Agreement checkboxes helper
function toggleAllAgreements(masterCheck) {
  const checkboxes = document.querySelectorAll('.agree-sub');
  checkboxes.forEach(chk => {
    chk.checked = masterCheck.checked;
  });
}

// ========================================================
// 1. Google OAuth 2.0 Standard Authentication Handlers
// ========================================================
let googleClientId = "";
let googleTokenClient = null;

async function initGoogleOAuth() {
  try {
    const res = await fetch('/api/auth/google/config');
    const json = await res.json();
    if (json.status === 'success' && json.client_id) {
      googleClientId = json.client_id;
      if (window.google && window.google.accounts) {
        // 1. OIDC ID Token Credential Init (One Tap & rendered buttons)
        google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleCredentialResponse,
          auto_select: false
        });

        // 2. OAuth 2.0 Token Client for explicit button clicks
        if (google.accounts.oauth2) {
          googleTokenClient = google.accounts.oauth2.initTokenClient({
            client_id: googleClientId,
            scope: 'openid email profile',
            callback: async (tokenResponse) => {
              if (tokenResponse && tokenResponse.access_token) {
                try {
                  const userInfoRes = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                    headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
                  });
                  const userInfo = await userInfoRes.json();
                  if (userInfo && userInfo.email) {
                    await executeGoogleOAuthLogin({
                      email: userInfo.email,
                      name: userInfo.name || '구글 회원',
                      google_id: userInfo.sub || ''
                    });
                  }
                } catch (e) {
                  console.error('Google userinfo fetch failed:', e);
                  openGoogleModal();
                }
              }
            }
          });
        }

        const container = document.getElementById('google-gis-container');
        if (container) {
          google.accounts.id.renderButton(container, {
            theme: 'outline',
            size: 'large',
            shape: 'pill',
            width: 300,
            text: 'signin_with'
          });
        }
      }
      const hint = document.getElementById('google-client-id-hint');
      if (hint) hint.classList.add('hidden');
    } else {
      const hint = document.getElementById('google-client-id-hint');
      if (hint) hint.classList.remove('hidden');
    }
  } catch (err) {
    console.warn("Google OAuth config load failed:", err);
  }
}

// Google Identity Services (OIDC / OAuth 2.0) Credential Callback
async function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) {
    alert("Google OAuth 2.0 인증 정보를 받지 못했습니다.");
    return;
  }
  await executeGoogleOAuthLogin({ credential: response.credential });
}

function openGoogleModal() {
  const modal = document.getElementById('google-auth-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeGoogleModal() {
  const modal = document.getElementById('google-auth-modal');
  if (modal) modal.classList.add('hidden');
}

// User clicked [Google 계정으로 계속하기]
async function handleGoogleLogin() {
  // 1. If OAuth 2.0 Token Client is initialized, trigger Google native OAuth popup
  if (googleTokenClient) {
    try {
      googleTokenClient.requestAccessToken();
      return;
    } catch (e) {
      console.warn("Token client request error:", e);
    }
  }

  // 2. Fallback to GIS prompt or standard dialog
  if (window.google && window.google.accounts && googleClientId) {
    try {
      google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          openGoogleModal();
        }
      });
      return;
    } catch (e) {
      console.warn("GIS prompt error:", e);
    }
  }
  openGoogleModal();
}

async function submitGoogleOAuthModal(event) {
  if (event) event.preventDefault();
  const email = document.getElementById('google-oauth-email')?.value?.trim();
  const name = document.getElementById('google-oauth-name')?.value?.trim() || "구글 회원";
  if (!email) {
    alert("Google 계정 이메일을 입력해 주세요.");
    return;
  }
  // Standard OAuth 2.0 token payload
  const mockSub = "gid_" + Math.random().toString(36).substring(2, 14);
  await executeGoogleOAuthLogin({ email, name, google_id: mockSub });
}

async function executeGoogleOAuthLogin(payload) {
  const submitBtn = document.getElementById('btn-google-modal-submit');
  const googleBtn = document.getElementById('btn-google-login');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span>OAuth 2.0 연동 중...</span>`;
  }
  if (googleBtn) googleBtn.disabled = true;

  try {
    const res = await fetch('/api/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const json = await res.json();
    if (!res.ok || json.status !== 'success') {
      throw new Error(json.detail || 'Google OAuth 2.0 인증에 실패했습니다.');
    }

    const userData = json.data;
    clearAuthUser();

    if (isUserAdmin(userData)) {
      userData.role = 'admin';
    }

    const remember = document.getElementById('login-remember')?.checked || false;
    setAuthUser(userData, remember);
    if (userData.profile?.user_conditions) {
      sessionStorage.setItem('youthfit_member_profile', JSON.stringify(userData.profile.user_conditions));
      if (remember) {
        localStorage.setItem('youthfit_member_profile', JSON.stringify(userData.profile.user_conditions));
      }
    }
    if (userData.profile?.recent_diagnosis) {
      sessionStorage.setItem('youthfit_diagnosis_result', JSON.stringify(userData.profile.recent_diagnosis));
      if (remember) {
        localStorage.setItem('youthfit_diagnosis_result', JSON.stringify(userData.profile.recent_diagnosis));
      }
    }

    closeGoogleModal();
    redirectAfterLogin(userData, true);
  } catch (err) {
    alert("Google OAuth 2.0 오류: " + err.message);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span class="material-symbols-outlined text-base">verified</span><span>OAuth 2.0 승인 및 로그인</span>`;
    }
    if (googleBtn) googleBtn.disabled = false;
  }
}

// ========================================================
// Helper to verify if user has admin privileges
function isUserAdmin(userData) {
  if (!userData) return false;
  const uRole = (userData.role || '').toLowerCase();
  const uEmail = (userData.email || '').toLowerCase();
  return uRole === 'admin' || uEmail === 'admin@youthfit.kr' || uEmail.startsWith('admin@') || uEmail === 'admin';
}

// ========================================================
// 2. Email / Password Login Handler
// ========================================================
async function handleLoginSubmit(event) {
  event.preventDefault();
  const emailInput = document.getElementById('login-email');
  let email = emailInput?.value?.trim() || '';
  const password = document.getElementById('login-password')?.value;
  const remember = document.getElementById('login-remember')?.checked || false;
  const submitBtn = event.target.querySelector('button[type="submit"]');

  if (!email || !password) {
    alert("아이디(또는 이메일)와 비밀번호를 모두 입력해 주세요.");
    return;
  }

  // 관리자 단축 아이디('admin') 입력 시 자동 정규화
  if (email.toLowerCase() === 'admin') {
    email = 'admin@youthfit.kr';
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>로그인 중...</span>`;
  }

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const json = await res.json();
    if (!res.ok || json.status !== 'success') {
      throw new Error(json.detail || '로그인 인증에 실패했습니다.');
    }

    const userData = json.data;
    clearAuthUser();

    if (isUserAdmin(userData)) {
      userData.role = 'admin';
    }

    // 세션(sessionStorage) 우선 저장 및 옵션 체크 시 지속(localStorage) 저장
    setAuthUser(userData, remember);

    if (userData.profile?.user_conditions) {
      sessionStorage.setItem('youthfit_member_profile', JSON.stringify(userData.profile.user_conditions));
      if (remember) {
        localStorage.setItem('youthfit_member_profile', JSON.stringify(userData.profile.user_conditions));
      }
    }
    if (userData.profile?.recent_diagnosis) {
      sessionStorage.setItem('youthfit_diagnosis_result', JSON.stringify(userData.profile.recent_diagnosis));
      if (remember) {
        localStorage.setItem('youthfit_diagnosis_result', JSON.stringify(userData.profile.recent_diagnosis));
      }
    }

    // Role-based immediate redirection
    redirectAfterLogin(userData);
  } catch (err) {
    alert("로그인 실패: " + err.message);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>로그인하기</span><span class="material-symbols-outlined text-lg">arrow_forward</span>`;
    }
  }
}

// Helper: Role-based immediate routing after login
function redirectAfterLogin(userData, isGoogleLogin = false) {
  const urlParams = new URLSearchParams(window.location.search);
  const redirect = urlParams.get('redirect');

  // 관리자 계정: 딜레이 없이 즉시 admin.html로 직행 렌더링
  if (isUserAdmin(userData)) {
    userData.role = 'admin';
    console.log('[Auth] Admin user detected. Immediately loading admin.html');
    window.location.replace('admin.html');
    return;
  }

  // 일반 회원:
  if (redirect && redirect.includes('admin')) {
    alert("접근하려던 페이지는 관리자 전용입니다. 일반 사용자 계정은 사용자 대시보드로 이동합니다.");
  }
  showToast(`✓ ${userData.name}님 환영합니다! 로그인에 성공했습니다.`, 'success');

  // 구글 계정 로그인 시: diagnosis.html(맞춤 진단 페이지)로 이동
  const isGoogle = isGoogleLogin || userData?.provider === 'google';
  const targetPage = isGoogle ? 'diagnosis.html' : (redirect || 'dashboard.html');

  setTimeout(() => {
    window.location.href = targetPage;
  }, 700);
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('redirect') === 'admin.html') {
    const banner = document.getElementById('admin-redirect-banner');
    if (banner) banner.classList.remove('hidden');
  }
  initGoogleOAuth();
});

// 3. Email Signup Handler
async function handleSignupSubmit(event) {
  event.preventDefault();
  const name = document.getElementById('signup-name')?.value?.trim();
  const email = document.getElementById('signup-email')?.value?.trim();
  const password = document.getElementById('signup-pwd')?.value;
  const passwordConfirm = document.getElementById('signup-pwd-confirm')?.value;
  const submitBtn = event.target.querySelector('button[type="submit"]');

  if (!name || !email || !password) {
    alert("모든 필수 항목을 입력해 주세요.");
    return;
  }

  if (password.length < 6) {
    alert("비밀번호는 최소 6자 이상으로 설정해 주세요.");
    return;
  }

  if (password !== passwordConfirm) {
    alert("비밀번호가 일치하지 않습니다. 다시 확인해 주세요.");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>가입 처리 중...</span>`;
  }

  try {
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password })
    });

    const json = await res.json();
    if (!res.ok || json.status !== 'success') {
      throw new Error(json.detail || '회원가입에 실패했습니다.');
    }

    const userData = json.data;
    clearAuthUser();
    setAuthUser(userData, false);
    showToast(`🎉 ${userData.name}님, 유스핏 AI 회원가입이 완료되었습니다! 1분 맞춤 진단으로 이동합니다.`, 'success');

    setTimeout(() => {
      window.location.href = 'diagnosis.html';
    }, 1000);
  } catch (err) {
    alert("회원가입 실패: " + err.message);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>10초 만에 간편 회원가입 완료</span><span class="material-symbols-outlined text-lg">done</span>`;
    }
  }
}

// 4. Guest Quick Start
function guestQuickStart() {
  window.location.href = 'diagnosis.html';
}

// Toast Notification Helper
function showToast(msg, type = 'info') {
  let toast = document.getElementById('auth-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'auth-toast';
    toast.className = 'fixed bottom-6 right-6 z-50 p-4 rounded-2xl bg-inverse-surface text-inverse-on-surface shadow-2xl text-xs font-semibold flex items-center gap-2 border border-outline/20 transition-all';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span class="material-symbols-outlined text-secondary text-lg">check_circle</span> <span>${msg}</span>`;
  toast.style.display = 'flex';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 3500);
}

// Check logged in user on page load
document.addEventListener('DOMContentLoaded', () => {
  try {
    const user = (typeof getAuthUser === 'function') ? getAuthUser() : null;
    if (user) {
      console.log("Logged in user:", user.email, user.name);
    }
  } catch (e) {}
});

// Window Exports
window.switchAuthTab = switchAuthTab;
window.togglePasswordVisibility = togglePasswordVisibility;
window.toggleAllAgreements = toggleAllAgreements;
window.handleGoogleLogin = handleGoogleLogin;
window.openGoogleModal = openGoogleModal;
window.closeGoogleModal = closeGoogleModal;
window.selectGoogleAccount = selectGoogleAccount;
window.submitGoogleModal = submitGoogleModal;
window.handleLoginSubmit = handleLoginSubmit;
window.handleSignupSubmit = handleSignupSubmit;
window.guestQuickStart = guestQuickStart;
window.showToast = showToast;
