/**
 * YouthFit AI - Diagnostic Dashboard & Dynamic Data Binding
 */

let currentPolicies = [];

document.addEventListener('DOMContentLoaded', () => {
  const heroProfileText = document.getElementById('hero-profile-text');
  const heroBenefitAmount = document.getElementById('hero-benefit-amount');
  const heroBenefitSubtext = document.getElementById('hero-benefit-subtext');
  const statPolicyCount = document.getElementById('stat-policy-count');
  const statDocsCount = document.getElementById('stat-docs-count');
  const policyContainer = document.getElementById('policy-cards-container');
  const docList = document.getElementById('doc-list');

  const progressText = document.getElementById('progress-text');
  const progressCircle = document.getElementById('progress-circle');
  const percentLabel = document.getElementById('percent-label');

  // Modal elements
  const modal = document.getElementById('policy-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalCloseBottom = document.getElementById('modal-close-bottom');

  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
  if (modalCloseBottom) modalCloseBottom.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  // Check member authentication & admin permissions
  const rawUser = localStorage.getItem('youthfit_user');
  const loggedInUser = rawUser ? JSON.parse(rawUser) : null;
  const isMember = !!(loggedInUser && (loggedInUser.id || loggedInUser.email));
  const uRole = (loggedInUser?.role || '').toLowerCase();
  const uEmail = (loggedInUser?.email || '').toLowerCase();
  const isAdmin = isMember && (uRole === 'admin' || uEmail === 'admin@youthfit.kr' || uEmail.startsWith('admin@') || uEmail === 'admin');

  // Sidebar admin monitoring button: ONLY visible to administrator accounts
  const sidebarAdminLink = document.getElementById('sidebar-admin-link');
  if (sidebarAdminLink) {
    if (isAdmin) {
      sidebarAdminLink.classList.remove('hidden');
      sidebarAdminLink.style.display = 'flex';
    } else {
      sidebarAdminLink.classList.add('hidden');
      sidebarAdminLink.style.display = 'none';
    }
  }

  // 1. Retrieve Result
  let result = null;
  try {
    if (isMember) {
      const raw = localStorage.getItem('youthfit_diagnosis_result');
      if (raw) {
        result = JSON.parse(raw);
      }
    } else {
      // Guest: read from temporary sessionStorage
      const transientRaw = sessionStorage.getItem('youthfit_transient_diagnosis_result');
      if (transientRaw) {
        result = JSON.parse(transientRaw);
      }
      // Requirement 1: Non-member diagnosis is one-time; remove transient profile
      sessionStorage.removeItem('youthfit_transient_profile');
      localStorage.removeItem('youthfit_profile');
    }
  } catch (e) {
    console.error("Failed to parse diagnosis result:", e);
  }

  // If admin lands on user dashboard, show convenient admin portal quick-jump banner
  if (isAdmin) {
    const banner = document.createElement('div');
    banner.id = 'admin-dashboard-notice';
    banner.className = 'bg-primary text-on-primary px-4 py-2.5 text-xs font-bold flex items-center justify-between shadow-md sticky top-16 z-50';
    banner.innerHTML = `
      <span class="flex items-center gap-2">
        <span class="material-symbols-outlined text-base">admin_panel_settings</span>
        <span>현재 최고 관리자 계정(${loggedInUser.email})으로 접속 중입니다.</span>
      </span>
      <a href="admin.html" class="px-3 py-1 bg-surface-container-lowest text-primary rounded-lg text-xs font-bold hover:bg-surface-container transition-colors inline-flex items-center gap-1 shadow-sm">
        <span>관리자 포털 바로가기</span>
        <span class="material-symbols-outlined text-sm">arrow_forward</span>
      </a>
    `;
    const mainContent = document.querySelector('.pl-0.md\\:pl-64') || document.body;
    mainContent.prepend(banner);
  }

  // If no result found, attempt fallback diagnosis
  if (!result) {
    let profile = { age: 24, district: '관악구', jobStatus: 'jobseeker', household: 'single', income: 'income60' };
    try {
      if (isMember) {
        const savedProf = localStorage.getItem('youthfit_member_profile');
        if (savedProf) profile = Object.assign(profile, JSON.parse(savedProf));
      }
    } catch (e) {}

    fetch('/api/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    })
      .then(r => r.json())
      .then(json => {
        if (json && json.status === 'success') {
          renderAll(json.data);
        }
      })
      .catch(e => console.error("Fallback diagnosis failed:", e));
  } else {
    renderAll(result);
  }

  function renderAll(data) {
    if (!data) return;
    currentPolicies = data.policies || [];

    // 2. Render Hero Banner Metrics
    if (data.profile && heroProfileText) {
      const summaryText = data.profile.summary || '맞춤 진단 완료';
      if (isMember && loggedInUser) {
        heroProfileText.textContent = `${loggedInUser.name} 님의 맞춤 진단: ${summaryText}`;
      } else {
        heroProfileText.textContent = `[비회원 일회성 진단] ${summaryText}`;
      }
    }
    if (data.total_benefit_formatted && heroBenefitAmount) {
      heroBenefitAmount.textContent = data.total_benefit_formatted;
    }
    if (data.total_benefit_text && heroBenefitSubtext) {
      heroBenefitSubtext.textContent = `(${data.total_benefit_text})`;
    }
    if (data.matched_count !== undefined && statPolicyCount) {
      statPolicyCount.textContent = `${data.matched_count}건`;
    }
    if (data.docs_count !== undefined && statDocsCount) {
      statDocsCount.textContent = `${data.docs_count}건`;
    }

    // Sidebar Score sync
    const sidebarScore = document.getElementById('sidebar-match-score');
    if (sidebarScore && currentPolicies.length > 0) {
      sidebarScore.textContent = `${currentPolicies[0].match_rate || 92}% 일치`;
    }

    // Dynamic Urgent Deadlines Count
    const urgentCount = currentPolicies.filter(p => getDeadlineInfo(p.apply_period).isUrgent).length;
    const heroUrgentBadge = document.getElementById('hero-urgent-badge');
    const heroUrgentText = document.getElementById('hero-urgent-text');
    const heroUrgentIcon = document.getElementById('hero-urgent-icon');
    if (heroUrgentBadge && heroUrgentText) {
      if (urgentCount > 0) {
        heroUrgentBadge.className = "flex items-center gap-2 px-4 py-2 rounded-xl bg-error-container text-on-error-container shadow-sm";
        if (heroUrgentIcon) {
          heroUrgentIcon.className = "material-symbols-outlined text-[16px] text-error";
          heroUrgentIcon.textContent = "alarm";
        }
        heroUrgentText.innerHTML = `마감 임박 <strong id="stat-urgent-count">${urgentCount}건</strong>`;
      } else {
        heroUrgentBadge.className = "flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-container text-on-surface shadow-sm border border-hairline-border";
        if (heroUrgentIcon) {
          heroUrgentIcon.className = "material-symbols-outlined text-[16px] text-secondary";
          heroUrgentIcon.textContent = "check_circle";
        }
        heroUrgentText.innerHTML = `마감 임박 <strong>0건 (여유)</strong>`;
      }
    }

    // 3. Render Dynamic Policy Cards
    if (currentPolicies.length > 0 && policyContainer) {
      renderPolicyCards(currentPolicies);
    }

    // 4. Render Dynamic Document Checklist
    if (data.checklist && data.checklist.length > 0 && docList) {
      renderChecklist(data.checklist);
    }
  }

  // Helper: Dynamic Deadline Info Calculation (No more hardcoded fake D-5)
  function getDeadlineInfo(periodStr) {
    if (!periodStr) {
      return {
        badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant text-xs font-medium"><span class="material-symbols-outlined text-[14px] text-secondary">check_circle</span><span>연중 상시 신청 가능</span></div>`,
        isUrgent: false
      };
    }

    const str = String(periodStr).trim();
    if (str.includes('상시') || str.includes('연중') || str.includes('수시') || str.includes('매월')) {
      return {
        badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary-container text-on-secondary-container text-xs font-semibold"><span class="material-symbols-outlined text-[14px]">all_inclusive</span><span>연중 상시 신청 가능</span></div>`,
        isUrgent: false
      };
    }

    // Parse date: ~ YYYY.MM.DD or ~ YYYY-MM-DD or ~ YYYYMMDD
    let endDate = null;
    const matchDots = str.match(/~\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})/);
    const matchCompact = str.match(/~\s*(\d{4})(\d{2})(\d{2})/);

    if (matchDots) {
      endDate = new Date(parseInt(matchDots[1]), parseInt(matchDots[2]) - 1, parseInt(matchDots[3]), 23, 59, 59);
    } else if (matchCompact) {
      endDate = new Date(parseInt(matchCompact[1]), parseInt(matchCompact[2]) - 1, parseInt(matchCompact[3]), 23, 59, 59);
    }

    if (endDate && !isNaN(endDate.getTime())) {
      const now = new Date();
      const diffMs = endDate.getTime() - now.getTime();
      const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays < 0) {
        return {
          badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-medium"><span class="material-symbols-outlined text-[14px]">event_busy</span><span>접수 마감</span></div>`,
          isUrgent: false
        };
      } else if (diffDays === 0) {
        return {
          badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-error text-on-error text-xs font-bold animate-pulse"><span class="material-symbols-outlined text-[14px]">alarm</span><span>D-Day 오늘 마감!</span></div>`,
          isUrgent: true
        };
      } else if (diffDays <= 7) {
        return {
          badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-error-container text-on-error-container text-xs font-bold"><span class="material-symbols-outlined text-[14px]">timer</span><span>D-${diffDays} 마감 임박</span></div>`,
          isUrgent: true
        };
      } else if (diffDays <= 30) {
        return {
          badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary-container text-on-primary-container text-xs font-semibold"><span class="material-symbols-outlined text-[14px]">schedule</span><span>D-${diffDays} 접수 중</span></div>`,
          isUrgent: false
        };
      } else {
        const cleanPeriod = str.split('(')[0].trim();
        return {
          badge: `<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant text-xs font-medium"><span class="material-symbols-outlined text-[14px]">calendar_today</span><span>${cleanPeriod}</span></div>`,
          isUrgent: false
        };
      }
    }

    return {
      badge: `<span class="text-xs text-on-surface-variant font-medium">${str}</span>`,
      isUrgent: false
    };
  }

  // Helper: Render Policy Cards
  function renderPolicyCards(policies) {
    const headerHtml = `
      <div class="flex items-center justify-between px-1">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary text-[24px]">recommend</span>
          <h2 class="text-xl font-bold text-on-surface">AI 선별 우선순위 혜택</h2>
        </div>
        <span class="text-xs text-on-surface-variant">정확도 및 적격 점수 순 정렬</span>
      </div>
    `;

    const cardsHtml = policies.map((p, idx) => {
      const isFirst = idx === 0;
      const rankBadgeColor = isFirst 
        ? 'bg-primary text-on-primary' 
        : idx === 1 
          ? 'bg-secondary text-on-secondary' 
          : 'bg-surface-container text-on-surface';

      // 정밀 계산된 마감일 뱃지 적용 (D-5 하드코딩 제거)
      const deadlineInfo = getDeadlineInfo(p.apply_period);
      const deadlineBadge = deadlineInfo.badge;

      const reasonsList = (p.reasons || []).map(r => `
        <span class="flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px] text-secondary">check_circle</span>
          ${r}
        </span>
      `).join('');

      return `
        <div class="civic-card p-6 space-y-5">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="flex items-center gap-2">
              <span class="px-2.5 py-1 rounded-full ${rankBadgeColor} text-xs font-bold">${p.rank_label}</span>
              <span class="px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant text-xs">${p.category}</span>
            </div>
            ${deadlineBadge}
          </div>

          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <h3 class="text-xl font-bold text-on-surface hover:text-primary transition-colors cursor-pointer" onclick="openPolicyModal(${idx})">${p.name}</h3>
              <div class="flex items-center gap-1 text-secondary font-bold text-sm">
                <span class="material-symbols-outlined text-[18px]">bolt</span>
                <span>적합도 ${p.match_rate}%</span>
              </div>
            </div>
            <p class="text-lg text-secondary font-bold">
              ${p.amount_desc}
            </p>
          </div>

          <!-- AI Logic Report Box -->
          <div class="rounded-xl bg-surface-container-low p-4 space-y-2 border border-hairline-border">
            <div class="flex items-center gap-2 text-primary text-xs font-semibold">
              <span class="material-symbols-outlined text-[18px]">psychology</span>
              <span>YouthFit AI 자격 판별 알고리즘 리포트</span>
            </div>
            <p class="text-xs text-on-surface-variant leading-relaxed">
              ${p.ai_summary}
            </p>
            <div class="pt-1 flex flex-wrap items-center gap-4 text-on-surface-variant text-xs">
              ${reasonsList}
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
            <div class="flex items-center gap-2 text-on-surface-variant text-xs">
              <span class="material-symbols-outlined text-[16px]">calendar_today</span>
              <span>신청기간: ${p.apply_period}</span>
            </div>
            <div class="flex items-center gap-2">
              <button class="px-3.5 py-2 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm border border-hairline-border cursor-pointer" onclick="openPolicyModal(${idx})" type="button">
                <span class="material-symbols-outlined text-[16px]">article</span>
                <span>공고문 AI 요약본</span>
              </button>
              <a class="px-4 py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-container text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm" href="${p.apply_url}" target="_blank" onclick="trackPolicyClick('${(p.policy_id || p.name).replace(/'/g, "\\'")}', '${p.name.replace(/'/g, "\\'")}', '${p.category.replace(/'/g, "\\'")}', 'apply')">
                <span>신청 바로가기</span>
                <span class="material-symbols-outlined text-[16px]">arrow_forward</span>
              </a>
            </div>
          </div>
        </div>
      `;
    }).join('');

    policyContainer.innerHTML = headerHtml + cardsHtml;
  }

  // Helper: Render Document Checklist (1:1 Service Page Mapping)
  function renderChecklist(items) {
    docList.innerHTML = items.map((doc, i) => {
      const isChecked = i === 0; // First pre-checked
      const actionLabel = doc.action_label || '정부24 무료 즉시 발급';
      const linkHtml = doc.link 
        ? `<div class="pt-1">
             <a class="inline-flex items-center gap-1 text-xs text-primary hover:underline font-semibold" href="${doc.link}" target="_blank" onclick="trackDocClick('${doc.name.replace(/'/g, "\\'")}')">
               <span>${actionLabel}</span>
               <span class="material-symbols-outlined text-[14px]">open_in_new</span>
             </a>
           </div>`
        : `<p class="text-xs text-on-surface-variant">온라인 신청 시 첨부 제출</p>`;

      return `
        <label class="flex items-start gap-3.5 p-3.5 rounded-xl bg-surface hover:bg-surface-container transition-colors cursor-pointer border border-hairline-border">
          <input ${isChecked ? 'checked' : ''} class="mt-1 w-4 h-4 rounded text-primary focus:ring-0 accent-primary cursor-pointer doc-item" data-id="${i}" type="checkbox">
          <div class="flex-1 space-y-0.5">
            <div class="flex items-center justify-between">
              <span class="text-sm font-bold text-on-surface">${doc.name}</span>
              <span class="doc-status-pill px-2 py-0.5 rounded-full ${isChecked ? 'bg-secondary-container text-on-secondary-container' : 'bg-surface-container-high text-on-surface-variant'} text-xs font-semibold">
                ${isChecked ? '준비 완료' : '미발급'}
              </span>
            </div>
            ${linkHtml}
          </div>
        </label>
      `;
    }).join('');

    bindChecklistListeners();
  }

  // Checklist Progress Logic
  function bindChecklistListeners() {
    const checkboxes = document.querySelectorAll('.doc-item');
    checkboxes.forEach(cb => {
      cb.addEventListener('change', updateChecklistProgress);
    });
    updateChecklistProgress();
  }

  function updateChecklistProgress() {
    const checkboxes = document.querySelectorAll('.doc-item');
    const total = checkboxes.length || 1;
    let checkedCount = 0;

    checkboxes.forEach(cb => {
      const statusPill = cb.closest('label')?.querySelector('.doc-status-pill');
      if (cb.checked) {
        checkedCount++;
        if (statusPill) {
          statusPill.className = "doc-status-pill px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-xs font-semibold";
          statusPill.textContent = "준비 완료";
        }
      } else {
        if (statusPill) {
          statusPill.className = "doc-status-pill px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-semibold";
          statusPill.textContent = "미발급";
        }
      }
    });

    const percent = Math.round((checkedCount / total) * 100);

    if (progressText) progressText.textContent = `${checkedCount}`;
    if (percentLabel) percentLabel.textContent = `${percent}%`;
    if (progressCircle) {
      progressCircle.setAttribute('stroke-dasharray', `${percent}, 100`);
    }
  }

  // Policy Click & View Tracking Telemetry
  window.trackPolicyClick = function(id, name, cat, actionType) {
    try {
      fetch('/api/stats/policy-click', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          policy_id: String(id || name),
          policy_name: name || '',
          category: cat || '',
          action_type: actionType || 'click'
        })
      }).catch(() => {});
    } catch (e) {}
  };

  window.trackDocClick = function(docName) {
    try {
      fetch('/api/stats/policy-click', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          policy_id: "DOC_ISSUANCE",
          policy_name: docName,
          category: "서류발급",
          action_type: "document"
        })
      }).catch(() => {});
    } catch (e) {}
  };

  // Modal Open Handler (Direct Application Page Binding)
  window.openPolicyModal = function(index) {
    const p = currentPolicies[index];
    if (!p || !modal) return;

    // Track modal open
    trackPolicyClick(p.policy_id || p.name, p.name, p.category, 'modal_open');

    document.getElementById('modal-rank').textContent = p.rank_label;
    document.getElementById('modal-category').textContent = p.category;
    document.getElementById('modal-title').textContent = p.name;
    document.getElementById('modal-amount').textContent = p.amount_desc;
    document.getElementById('modal-ai-report').textContent = p.ai_summary;
    document.getElementById('modal-period').textContent = p.apply_period;
    document.getElementById('modal-dept').textContent = p.category.split('/')[1]?.trim() || '서울특별시';
    document.getElementById('modal-content').textContent = p.explanation || p.support_content || '상세 공고 내용을 확인하세요.';
    
    const docsUl = document.getElementById('modal-docs');
    if (docsUl) {
      docsUl.innerHTML = (p.docs || ['주민등록표초본', '신분증 사본']).map(d => `<li>${d}</li>`).join('');
    }

    const applyLink = document.getElementById('modal-apply-link');
    if (applyLink) {
      applyLink.href = p.apply_url || 'https://youth.seoul.go.kr';
      applyLink.onclick = () => {
        trackPolicyClick(p.policy_id || p.name, p.name, p.category, 'apply');
      };
    }

    modal.classList.remove('hidden');
  };

  function closeModal() {
    if (modal) modal.classList.add('hidden');
  }

  // Toast Function
  window.showToast = function(message) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-message');
    if (toast && toastMsg) {
      toastMsg.textContent = message;
      toast.classList.remove('hidden');
      setTimeout(() => {
        toast.classList.add('hidden');
      }, 3000);
    }
  };

  // Kakao Share Handler
  window.handleKakaoShare = function() {
    let profileDesc = "2026 유스핏 AI 맞춤 청년 정책 진단 결과\n";
    if (heroProfileText) profileDesc += `• 대상: ${heroProfileText.textContent}\n`;
    if (heroBenefitAmount) profileDesc += `• 예상 수혜금액: 연 ${heroBenefitAmount.textContent}원 상당\n`;
    profileDesc += "\n[추천 혜택 Top 4]\n";
    currentPolicies.slice(0, 4).forEach((p, idx) => {
      profileDesc += `${idx+1}. ${p.name} (${p.amount_desc})\n`;
    });
    profileDesc += "\n서류 발급 링크: https://www.gov.kr\n진단 사이트: http://127.0.0.1:8000";

    if (navigator.clipboard) {
      navigator.clipboard.writeText(profileDesc)
        .then(() => {
          showToast("📋 진단 결과 및 서류 목록이 클립보드에 복사되었습니다! 카카오톡에 붙여넣어 공유하세요.");
        })
        .catch(() => {
          alert(profileDesc);
        });
    } else {
      alert(profileDesc);
    }
  };
});
