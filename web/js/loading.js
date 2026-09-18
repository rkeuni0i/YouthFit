/**
 * YouthFit AI - Neural Match Engine Simulation & Pipeline Progress
 */

document.addEventListener('DOMContentLoaded', () => {
  let progress = 20;
  const progressText = document.getElementById('progress-percentage');
  const progressCircle = document.getElementById('progress-circle');
  const step3Status = document.getElementById('step3-status');
  const step4Card = document.getElementById('step4-card');
  const step4Status = document.getElementById('step4-status');
  const userConditionEl = document.getElementById('user-condition-title');
  const circumference = 314.159;

  let profile = {
    age: 24,
    district: '관악구',
    jobStatus: 'jobseeker',
    household: 'single',
    income: 'income60'
  };

  // Check login authentication state
  const rawUser = sessionStorage.getItem('youthfit_user') || localStorage.getItem('youthfit_user');
  const loggedInUser = rawUser ? JSON.parse(rawUser) : null;
  const isMember = !!(loggedInUser && loggedInUser.id);

  // Retrieve customized profile if present
  try {
    if (isMember) {
      const saved = sessionStorage.getItem('youthfit_member_profile') || localStorage.getItem('youthfit_member_profile') || (loggedInUser.profile?.user_conditions ? JSON.stringify(loggedInUser.profile.user_conditions) : null);
      if (saved) {
        profile = Object.assign(profile, JSON.parse(saved));
      }
    } else {
      // Guest: read strictly from temporary sessionStorage
      const transient = sessionStorage.getItem('youthfit_transient_profile');
      if (transient) {
        profile = Object.assign(profile, JSON.parse(transient));
      }
      localStorage.removeItem('youthfit_profile');
    }

    if (profile.age && userConditionEl) {
      const jobDescMap = {
        jobseeker: '취준생',
        employed: '재직자',
        freelancer: '프리랜서',
        student: '대학(원)생'
      };
      const jobDesc = jobDescMap[profile.jobStatus] || '청년';
      const regTitle = profile.region === '전국' 
        ? '전국' 
        : `${profile.regionFull || profile.region || '서울'} ${profile.district || ''}`.trim();
      userConditionEl.textContent = `${regTitle} ${profile.age}세 ${jobDesc}`;
    }
  } catch (e) {
    console.error("Profile load error:", e);
  }

  // 1. Trigger Backend AI Diagnosis API Call
  let apiDone = false;
  fetch('/api/diagnose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile)
  })
    .then(res => res.json())
    .then(json => {
      if (json && json.status === 'success') {
        if (isMember) {
          sessionStorage.setItem('youthfit_diagnosis_result', JSON.stringify(json.data));
          if (localStorage.getItem('youthfit_user')) {
            localStorage.setItem('youthfit_diagnosis_result', JSON.stringify(json.data));
          }
          // Persist to user DB
          fetch('/api/user/save-diagnosis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: loggedInUser.id,
              profile: profile,
              diagnosis_result: json.data
            })
          }).catch(e => console.warn("Member DB save error:", e));
        } else {
          // Guest: store only in sessionStorage for one-time viewing
          sessionStorage.setItem('youthfit_transient_diagnosis_result', JSON.stringify(json.data));
          localStorage.removeItem('youthfit_diagnosis_result');
        }
        console.log("Diagnosis result ready:", json.data);
      }
      apiDone = true;
    })
    .catch(err => {
      console.warn("Diagnosis API error (using offline fallback):", err);
      apiDone = true;
    });

  // 2. Smooth Loading Animation
  const interval = setInterval(() => {
    if (progress < 95) {
      progress += Math.floor(Math.random() * 8) + 3;
      if (progress > 95) progress = 95;
    } else if (progress >= 95 && progress < 100) {
      if (apiDone) {
        progress = 100;
      }
    }

    if (progressText) progressText.textContent = `${Math.min(progress, 100)}%`;
    if (progressCircle) {
      const offset = circumference - (Math.min(progress, 100) / 100) * circumference;
      progressCircle.style.strokeDashoffset = offset;
    }

    // Step 4 packaging trigger around 90%
    if (progress >= 90 && step4Card && step4Status) {
      step4Card.className = "group flex items-start gap-4 p-3.5 rounded-lg bg-surface-container-low transition-all";
      step4Status.className = "font-label-md text-label-md px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-semibold";
      step4Status.textContent = "패키징 완료";
    }

    if (progress >= 100) {
      clearInterval(interval);
      if (progressText) progressText.textContent = "100%";
      if (step3Status) {
        step3Status.textContent = "판별 완료";
      }

      // Transition to dashboard after brief pause
      setTimeout(() => {
        window.location.href = 'dashboard.html';
      }, 700);
    }
  }, 120);
});
