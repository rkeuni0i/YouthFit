/**
 * YouthFit AI - Authentication & Google OAuth Logic with Database Persistence
 */

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

// 1. Google OAuth Social Login Modal & Handlers
function openGoogleModal() {
  const modal = document.getElementById('google-auth-modal');
  if (modal) {
    modal.classList.remove('hidden');
  }
}

function closeGoogleModal() {
  const modal = document.getElementById('google-auth-modal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

function handleGoogleLogin() {
  openGoogleModal();
}

function selectGoogleAccount(email, name) {
  const emailInput = document.getElementById('google-modal-email');
  const nameInput = document.getElementById('google-modal-name');
  if (emailInput) emailInput.value = email;
  if (nameInput) nameInput.value = name;
  executeGoogleLogin(email, name);
}

async function submitGoogleModal(event) {
  if (event) event.preventDefault();
  const email = document.getElementById('google-modal-email')?.value?.trim();
  const name = document.getElementById('google-modal-name')?.value?.trim() || "구글 사용자";
  if (!email) {
    alert("Google 이메일을 입력해 주세요.");
    return;
  }
  await executeGoogleLogin(email, name);
}

async function executeGoogleLogin(email, name) {
  const btn = document.getElementById('btn-google-modal-submit');
  const googleBtn = document.getElementById('btn-google-login');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span>로그인 중...</span>`;
  }
  if (googleBtn) googleBtn.disabled = true;

  try {
    const res = await fetch('/api/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.trim(),
        name: name.trim(),
        google_id: "gid_" + Math.random().toString(36).substring(2, 10)
      })
    });

    const json = await res.json();
    if (!res.ok || json.status !== 'success') {
      throw new Error(json.detail || 'Google 로그인에 실패했습니다.');
    }

    const userData = json.data;
    // Purge any old guest data from storage so it does not bleed into the logged in user
    localStorage.removeItem('youthfit_profile');
    sessionStorage.clear();

    localStorage.setItem('youthfit_user', JSON.stringify(userData));
    if (userData.profile?.user_conditions) {
      localStorage.setItem('youthfit_member_profile', JSON.stringify(userData.profile.user_conditions));
    }
    if (userData.profile?.recent_diagnosis) {
      localStorage.setItem('youthfit_diagnosis_result', JSON.stringify(userData.profile.recent_diagnosis));
    }

    closeGoogleModal();
    showToast(`🎉 ${userData.name}님 환영합니다! Google 계정으로 로그인되었습니다.`, 'success');

    setTimeout(() => {
      window.location.href = 'dashboard.html';
    }, 1000);
  } catch (err) {
    alert("Google 로그인 오류: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>로그인 진행</span><span class="material-symbols-outlined text-base">login</span>`;
    }
    if (googleBtn) googleBtn.disabled = false;
  }
}

// 2. Email / Password Login Handler
async function handleLoginSubmit(event) {
  event.preventDefault();
  const email = document.getElementById('login-email')?.value?.trim();
  const password = document.getElementById('login-password')?.value;
  const submitBtn = event.target.querySelector('button[type="submit"]');

  if (!email || !password) {
    alert("이메일과 비밀번호를 모두 입력해 주세요.");
    return;
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
    // Requirement 1: Purge any old guest data
    localStorage.removeItem('youthfit_profile');
    sessionStorage.clear();

    localStorage.setItem('youthfit_user', JSON.stringify(userData));
    if (userData.profile?.user_conditions) {
      localStorage.setItem('youthfit_member_profile', JSON.stringify(userData.profile.user_conditions));
    }
    if (userData.profile?.recent_diagnosis) {
      localStorage.setItem('youthfit_diagnosis_result', JSON.stringify(userData.profile.recent_diagnosis));
    }

    showToast(`✓ ${userData.name}님 환영합니다! 로그인에 성공했습니다.`, 'success');

    setTimeout(() => {
      window.location.href = 'dashboard.html';
    }, 800);
  } catch (err) {
    alert("로그인 실패: " + err.message);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>로그인하기</span><span class="material-symbols-outlined text-lg">arrow_forward</span>`;
    }
  }
}

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
    // Requirement 1: Purge any guest residual profile so user starts clean
    localStorage.removeItem('youthfit_profile');
    sessionStorage.clear();

    localStorage.setItem('youthfit_user', JSON.stringify(userData));
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
    const userRaw = localStorage.getItem('youthfit_user');
    if (userRaw) {
      const user = JSON.parse(userRaw);
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
