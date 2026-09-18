/**
 * YouthFit AI - Nationwide 17-Region & District Survey Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  const state = {
    age: 24,
    region: '서울',
    regionFull: '서울특별시',
    district: '관악구',
    jobStatus: 'jobseeker',
    household: 'single',
    income: 'income60'
  };

  // Nationwide Region & District Data Directory
  const DISTRICT_DATA = {
    '서울': {
      full: '서울특별시',
      districts: ['관악구', '마포구', '강남구', '성동구', '영등포구', '종로구', '중구', '용산구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '양천구', '강서구', '구로구', '금천구', '동작구', '서초구', '송파구', '강동구', '서울 전체']
    },
    '경기': {
      full: '경기도',
      districts: ['수원시', '성남시', '고양시', '용인시', '부천시', '안산시', '화성시', '평택시', '안양시', '시흥시', '파주시', '김포시', '의정부시', '광주시', '하남시', '경기 전체']
    },
    '인천': {
      full: '인천광역시',
      districts: ['부평구', '남동구', '연수구', '서구', '미추홀구', '계양구', '중구', '동구', '인천 전체']
    },
    '부산': {
      full: '부산광역시',
      districts: ['해운대구', '부산진구', '남구', '동래구', '금정구', '사하구', '북구', '연제구', '수영구', '사상구', '기장군', '부산 전체']
    },
    '대구': {
      full: '대구광역시',
      districts: ['수성구', '달서구', '북구', '중구', '동구', '서구', '남구', '달성군', '대구 전체']
    },
    '광주': {
      full: '광주광역시',
      districts: ['북구', '서구', '광산구', '동구', '남구', '광주 전체']
    },
    '대전': {
      full: '대전광역시',
      districts: ['유성구', '서구', '중구', '동구', '대덕구', '대전 전체']
    },
    '울산': {
      full: '울산광역시',
      districts: ['남구', '중구', '북구', '동구', '울주군', '울산 전체']
    },
    '세종': {
      full: '세종특별자치시',
      districts: ['세종시 전체']
    },
    '강원': {
      full: '강원특별자치도',
      districts: ['춘천시', '원주시', '강릉시', '동해시', '속초시', '강원 전체']
    },
    '충북': {
      full: '충청북도',
      districts: ['청주시', '충주시', '제천시', '음성군', '진천군', '충북 전체']
    },
    '충남': {
      full: '충청남도',
      districts: ['천안시', '아산시', '서산시', '당진시', '논산시', '공주시', '충남 전체']
    },
    '전북': {
      full: '전북특별자치도',
      districts: ['전주시', '익산시', '군산시', '정읍시', '남원시', '전북 전체']
    },
    '전남': {
      full: '전라남도',
      districts: ['여수시', '순천시', '목포시', '광양시', '나주시', '무안군', '전남 전체']
    },
    '경북': {
      full: '경상북도',
      districts: ['포항시', '구미시', '경주시', '경산시', '안동시', '김천시', '경북 전체']
    },
    '경남': {
      full: '경상남도',
      districts: ['창원시', '김해시', '양산시', '진주시', '거제시', '통영시', '경남 전체']
    },
    '제주': {
      full: '제주특별자치도',
      districts: ['제주시', '서귀포시', '제주 전체']
    },
    '전국': {
      full: '전국 공통',
      districts: ['전국 어디나']
    }
  };

  // DOM Elements
  const ageInput = document.getElementById('age-input');
  const currentRegionText = document.getElementById('current-region-text');
  const districtStepTitle = document.getElementById('district-step-title');
  const districtChipsContainer = document.getElementById('district-chips-container');
  const btnToggleAllProvinces = document.getElementById('btn-toggle-all-provinces');
  const provinceAllPanel = document.getElementById('province-all-panel');
  const provinceToggleLabel = document.getElementById('province-toggle-label');

  const provinceBtns = document.querySelectorAll('.province-btn');
  const subProvinceBtns = document.querySelectorAll('.sub-province-btn');

  const jobStatusCards = document.querySelectorAll('#job-status-group > div');
  const householdBtns = document.querySelectorAll('#household-group button');
  const incomeBtns = document.querySelectorAll('#income-group button');
  const startBtn = document.getElementById('start-diagnosis-btn');

  const estimateAmountEl = document.getElementById('estimate-amount');
  const estimateSubtextEl = document.getElementById('estimate-subtext');
  const barYouthAllowance = document.getElementById('bar-youth-allowance');
  const textYouthAllowance = document.getElementById('text-youth-allowance');
  const barRentSupport = document.getElementById('bar-rent-support');
  const textRentSupport = document.getElementById('text-rent-support');

  const userBannerEl = document.getElementById('diagnosis-user-banner');

  // Check login authentication state
  const rawUser = sessionStorage.getItem('youthfit_user') || localStorage.getItem('youthfit_user');
  const loggedInUser = rawUser ? JSON.parse(rawUser) : null;
  const isMember = !!(loggedInUser && loggedInUser.id);

  // Render User Banner
  if (userBannerEl) {
    if (isMember) {
      userBannerEl.innerHTML = `
        <div class="p-3.5 rounded-xl bg-primary-fixed/40 border border-primary/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-xl">account_circle</span>
            <span class="text-xs sm:text-sm text-on-surface">
              <strong>${loggedInUser.name} 님</strong> (정식 회원) 맞춤 진단 모드입니다. 변경된 조건은 계정 DB에 영구 보관됩니다.
            </span>
          </div>
          <span class="px-2.5 py-1 rounded-full bg-primary-container text-on-primary text-[11px] font-bold self-start sm:self-auto shrink-0">
            회원 프로필 동기화 ON
          </span>
        </div>
      `;
    } else {
      userBannerEl.innerHTML = `
        <div class="p-3.5 rounded-xl bg-surface-container-low border border-hairline-border flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary text-xl">bolt</span>
            <span class="text-xs sm:text-sm text-on-surface-variant">
              <strong>비회원 일회성 진단 모드:</strong> 입력하신 정보는 브라우저 세션에만 임시 활용되며 DB 및 기기에 영구 보관되지 않습니다.
            </span>
          </div>
          <a href="auth.html" class="text-xs text-primary font-bold hover:underline shrink-0 flex items-center gap-0.5">
            <span>로그인/회원가입</span>
            <span class="material-symbols-outlined text-xs">arrow_forward</span>
          </a>
        </div>
      `;
    }
  }

  // Requirement 1: Only remember profile for logged-in members.
  // One-time guest diagnosis MUST NOT remember information!
  if (isMember) {
    try {
      const savedProf = localStorage.getItem('youthfit_member_profile');
      const userProf = loggedInUser.profile?.user_conditions || (savedProf ? JSON.parse(savedProf) : null);
      if (userProf) {
        Object.assign(state, userProf);
      }
    } catch (e) {
      console.warn("Member profile load error:", e);
    }
  } else {
    // Guest: purge any old guest data from localStorage so information is NOT remembered
    try {
      localStorage.removeItem('youthfit_profile');
      localStorage.removeItem('youthfit_diagnosis_result');
    } catch (e) {}
  }

  // 1. Age Input
  if (ageInput) {
    ageInput.value = state.age;
    ageInput.addEventListener('input', (e) => {
      let val = parseInt(e.target.value, 10);
      if (isNaN(val)) val = 24;
      state.age = Math.max(15, Math.min(val, 39));
      recalculateEstimate();
    });
  }

  // 2. Nationwide Region & District Selector Logic
  function setProvince(provinceShort) {
    const provData = DISTRICT_DATA[provinceShort] || DISTRICT_DATA['서울'];
    state.region = provinceShort;
    state.regionFull = provData.full;

    // Highlight active province button
    const allProvButtons = [...provinceBtns, ...subProvinceBtns];
    allProvButtons.forEach(b => {
      const p = b.getAttribute('data-province');
      if (p === provinceShort) {
        b.className = b.classList.contains('province-btn')
          ? "province-btn py-2.5 px-2 rounded-lg text-xs sm:text-sm text-center font-bold transition-all bg-primary text-on-primary shadow-sm flex items-center justify-center gap-1"
          : "sub-province-btn px-2 py-1.5 rounded-lg text-xs text-center bg-primary text-on-primary font-bold shadow-sm";
        if (b.classList.contains('province-btn')) {
          b.innerHTML = `<span class="material-symbols-outlined text-xs">check</span> ${p}`;
        }
      } else {
        b.className = b.classList.contains('province-btn')
          ? "province-btn py-2.5 px-2 rounded-lg text-xs sm:text-sm text-center transition-all bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high"
          : "sub-province-btn px-2 py-1.5 rounded-lg text-xs text-center bg-surface-container-lowest hover:bg-primary-fixed text-on-surface-variant";
        if (b.classList.contains('province-btn')) {
          b.textContent = p;
        }
      }
    });

    // Update Step 2 Title
    if (districtStepTitle) {
      districtStepTitle.textContent = `2단계: ${state.regionFull} 세부 지역구 선택`;
    }

    // Default district for new province if current district does not belong
    if (!provData.districts.includes(state.district)) {
      state.district = provData.districts[0] || '전체';
    }

    renderDistrictChips(provData.districts);
    updateCurrentRegionDisplay();
    recalculateEstimate();
  }

  function renderDistrictChips(districts) {
    if (!districtChipsContainer) return;

    districtChipsContainer.innerHTML = districts.map(dist => {
      const isSelected = dist === state.district;
      const activeClass = isSelected
        ? "py-2 px-2.5 rounded-lg text-xs sm:text-sm font-bold bg-primary-container text-on-primary shadow-sm flex items-center justify-center gap-1 district-chip"
        : "py-2 px-2.5 rounded-lg text-xs sm:text-sm text-center bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant transition-colors district-chip";

      const checkIcon = isSelected ? '<span class="material-symbols-outlined text-xs">check</span>' : '';

      return `
        <button type="button" class="${activeClass}" data-district="${dist}">
          ${checkIcon} <span>${dist}</span>
        </button>
      `;
    }).join('');

    // Bind chip clicks
    districtChipsContainer.querySelectorAll('.district-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const selectedDist = chip.getAttribute('data-district');
        state.district = selectedDist;

        districtChipsContainer.querySelectorAll('.district-chip').forEach(c => {
          const d = c.getAttribute('data-district');
          if (d === selectedDist) {
            c.className = "py-2 px-2.5 rounded-lg text-xs sm:text-sm font-bold bg-primary-container text-on-primary shadow-sm flex items-center justify-center gap-1 district-chip";
            c.innerHTML = `<span class="material-symbols-outlined text-xs">check</span> <span>${d}</span>`;
          } else {
            c.className = "py-2 px-2.5 rounded-lg text-xs sm:text-sm text-center bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant transition-colors district-chip";
            c.innerHTML = `<span>${d}</span>`;
          }
        });

        updateCurrentRegionDisplay();
        recalculateEstimate();
      });
    });
  }

  function updateCurrentRegionDisplay() {
    if (currentRegionText) {
      if (state.region === '전국') {
        currentRegionText.textContent = "전국 공통 정책 적용";
      } else {
        currentRegionText.textContent = `${state.regionFull} ${state.district}`;
      }
    }
  }

  // Toggle All Provinces Panel
  if (btnToggleAllProvinces && provinceAllPanel) {
    btnToggleAllProvinces.addEventListener('click', () => {
      const isHidden = provinceAllPanel.classList.contains('hidden');
      provinceAllPanel.classList.toggle('hidden');
      if (provinceToggleLabel) {
        provinceToggleLabel.textContent = isHidden ? '시·도 패널 닫기' : '전체 17개 시·도 보기';
      }
    });
  }

  // Province Click Listeners
  provinceBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      setProvince(btn.getAttribute('data-province'));
    });
  });

  subProvinceBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      setProvince(btn.getAttribute('data-province'));
    });
  });

  // Initial Province Render
  setProvince(state.region || '서울');

  // 3. Job Status Selector
  jobStatusCards.forEach(card => {
    card.addEventListener('click', () => {
      const selectedStatus = card.getAttribute('data-status') || 'jobseeker';
      state.jobStatus = selectedStatus;

      jobStatusCards.forEach(c => {
        const isCurrent = c.getAttribute('data-status') === selectedStatus;
        const circle = c.querySelector('span.rounded-full:last-child');
        const titleEl = c.querySelector('div > p:first-child');

        if (isCurrent) {
          c.className = "p-4 rounded-xl bg-surface-container-high text-on-surface cursor-pointer shadow-sm flex items-start justify-between border border-primary";
          if (titleEl) titleEl.className = "font-bold text-primary text-base";
          if (circle) {
            circle.className = "w-5 h-5 rounded-full bg-primary text-on-primary flex items-center justify-center";
            circle.innerHTML = '<span class="material-symbols-outlined text-xs">check</span>';
          }
        } else {
          c.className = "p-4 rounded-xl bg-surface-container-lowest hover:bg-surface-container-low text-on-surface cursor-pointer transition-colors shadow-sm flex items-start justify-between border border-hairline-border";
          if (titleEl) titleEl.className = "font-semibold text-on-surface text-base";
          if (circle) {
            circle.className = "w-5 h-5 rounded-full bg-surface-container-high";
            circle.innerHTML = "";
          }
        }
      });

      recalculateEstimate();
    });
  });

  // 4. Household Buttons
  householdBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const selected = btn.getAttribute('data-household') || 'single';
      state.household = selected;

      householdBtns.forEach(b => {
        const isCurrent = b.getAttribute('data-household') === selected;
        const icon = b.querySelector('.material-symbols-outlined');
        const titleEl = b.querySelector('div > p:first-child');

        if (isCurrent) {
          b.className = "p-3.5 rounded-lg bg-surface-container-high text-left flex flex-col justify-between gap-2 shadow-sm border border-primary";
          if (icon) icon.className = "material-symbols-outlined text-primary";
          if (titleEl) titleEl.className = "text-xs sm:text-sm font-bold text-primary";
        } else {
          b.className = "p-3.5 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-left flex flex-col justify-between gap-2 transition-colors border border-hairline-border";
          if (icon) icon.className = "material-symbols-outlined text-outline";
          if (titleEl) titleEl.className = "text-xs sm:text-sm font-semibold text-on-surface";
        }
      });

      recalculateEstimate();
    });
  });

  // 5. Income Buttons
  incomeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const selected = btn.getAttribute('data-income') || 'income60';
      state.income = selected;

      incomeBtns.forEach(b => {
        const isCurrent = b.getAttribute('data-income') === selected;
        const titleEl = b.querySelector('p:first-child');

        if (isCurrent) {
          b.className = "p-3 rounded-lg bg-surface-container-high text-left shadow-sm border border-primary";
          if (titleEl) titleEl.className = "text-xs font-bold text-primary";
        } else {
          b.className = "p-3 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-left transition-colors border border-hairline-border";
          if (titleEl) titleEl.className = "text-xs font-semibold text-on-surface";
        }
      });

      recalculateEstimate();
    });
  });

  // Real-time Sidebar Calculation Engine
  function recalculateEstimate() {
    let amount = 0;
    let allowanceMatch = 90;
    let rentMatch = 75;
    let subtext = "";

    // 1. Economic status benefit
    if (state.jobStatus === 'jobseeker') {
      amount += 3000000;
      allowanceMatch = 98;
      if (state.region === '서울') {
        subtext = "서울시 청년수당(월 50만원×6회)";
      } else if (state.region === '광주') {
        subtext = "광주 청년 구직활동수당(월 50만원×6회)";
      } else {
        subtext = "국민취업지원제도 구직촉진수당(월 50만원×6회)";
      }
    } else if (state.jobStatus === 'employed') {
      amount += 3600000;
      allowanceMatch = 55;
      if (state.region === '서울') {
        subtext = "희망두배 청년통장 자산형성 매칭(연 최대 360만원)";
      } else if (state.region === '경기') {
        subtext = "경기 청년 복지포인트(연 120만) + 도약계좌 매칭";
      } else {
        subtext = "청년도약계좌 정부기여금 매칭(연 최대 300만원)";
      }
    } else if (state.jobStatus === 'student') {
      amount += 500000;
      allowanceMatch = 40;
      subtext = `${state.regionFull} 대학생 교통비 및 학자금 이자지원`;
    } else {
      amount += 1200000;
      allowanceMatch = 75;
      subtext = "프리랜서 역량개발 및 자격증 응시료 지원";
    }

    // 2. Housing benefit
    if (state.household === 'single') {
      if (state.income === 'income60' || state.income === 'income120') {
        amount += 2400000; // 월 20만원 x 12개월
        rentMatch = 96;
        subtext += ` + ${state.region === '부산' ? '부산' : state.region === '서울' ? '서울' : '청년'} 월세 특별지원`;
      } else {
        rentMatch = 70;
      }
    } else {
      rentMatch = 35;
    }

    // 3. Transportation benefit (Age 19~24)
    if (state.age >= 19 && state.age <= 24) {
      amount += 100000;
    }

    if (estimateAmountEl) {
      estimateAmountEl.textContent = amount.toLocaleString('ko-KR');
    }
    if (estimateSubtextEl) {
      estimateSubtextEl.textContent = subtext;
    }
    if (barYouthAllowance) {
      barYouthAllowance.style.width = `${allowanceMatch}%`;
    }
    if (textYouthAllowance) {
      textYouthAllowance.textContent = `${allowanceMatch}% ${allowanceMatch > 80 ? '매우 높음' : '적합'}`;
    }
    if (barRentSupport) {
      barRentSupport.style.width = `${rentMatch}%`;
    }
    if (textRentSupport) {
      textRentSupport.textContent = `${rentMatch}% ${rentMatch > 80 ? '통과 예상' : '검토 필요'}`;
    }
  }

  // Synchronize UI visuals with current state (useful for members who have saved conditions)
  function syncFormVisuals() {
    if (ageInput) ageInput.value = state.age;
    setProvince(state.region || '서울');

    jobStatusCards.forEach(c => {
      const isCurrent = c.getAttribute('data-status') === state.jobStatus;
      const circle = c.querySelector('span.rounded-full:last-child');
      const titleEl = c.querySelector('div > p:first-child');
      if (isCurrent) {
        c.className = "p-4 rounded-xl bg-surface-container-high text-on-surface cursor-pointer shadow-sm flex items-start justify-between border border-primary";
        if (titleEl) titleEl.className = "font-bold text-primary text-base";
        if (circle) {
          circle.className = "w-5 h-5 rounded-full bg-primary text-on-primary flex items-center justify-center";
          circle.innerHTML = '<span class="material-symbols-outlined text-xs">check</span>';
        }
      } else {
        c.className = "p-4 rounded-xl bg-surface-container-lowest hover:bg-surface-container-low text-on-surface cursor-pointer transition-colors shadow-sm flex items-start justify-between border border-hairline-border";
        if (titleEl) titleEl.className = "font-semibold text-on-surface text-base";
        if (circle) {
          circle.className = "w-5 h-5 rounded-full bg-surface-container-high";
          circle.innerHTML = "";
        }
      }
    });

    householdBtns.forEach(b => {
      const isCurrent = b.getAttribute('data-household') === state.household;
      const icon = b.querySelector('.material-symbols-outlined');
      const titleEl = b.querySelector('div > p:first-child');
      if (isCurrent) {
        b.className = "p-3.5 rounded-lg bg-surface-container-high text-left flex flex-col justify-between gap-2 shadow-sm border border-primary";
        if (icon) icon.className = "material-symbols-outlined text-primary";
        if (titleEl) titleEl.className = "text-xs sm:text-sm font-bold text-primary";
      } else {
        b.className = "p-3.5 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-left flex flex-col justify-between gap-2 transition-colors border border-hairline-border";
        if (icon) icon.className = "material-symbols-outlined text-outline";
        if (titleEl) titleEl.className = "text-xs sm:text-sm font-semibold text-on-surface";
      }
    });

    incomeBtns.forEach(b => {
      const isCurrent = b.getAttribute('data-income') === state.income;
      const titleEl = b.querySelector('p:first-child');
      if (isCurrent) {
        b.className = "p-3 rounded-lg bg-surface-container-high text-left shadow-sm border border-primary";
        if (titleEl) titleEl.className = "text-xs font-bold text-primary";
      } else {
        b.className = "p-3 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-left transition-colors border border-hairline-border";
        if (titleEl) titleEl.className = "text-xs font-semibold text-on-surface";
      }
    });
  }

  // Initial synchronization of controls with state
  syncFormVisuals();

  // Trigger calculation
  recalculateEstimate();

  // Start Diagnosis: Save profile & navigate to loading.html
  if (startBtn) {
    startBtn.addEventListener('click', () => {
      if (isMember) {
        // Logged-in member: remember info in sessionStorage & optional localStorage, sync with user DB
        try {
          sessionStorage.setItem('youthfit_member_profile', JSON.stringify(state));
          if (localStorage.getItem('youthfit_user')) {
            localStorage.setItem('youthfit_member_profile', JSON.stringify(state));
          }
          if (loggedInUser) {
            loggedInUser.profile = loggedInUser.profile || {};
            loggedInUser.profile.user_conditions = state;
            sessionStorage.setItem('youthfit_user', JSON.stringify(loggedInUser));
            if (localStorage.getItem('youthfit_user')) {
              localStorage.setItem('youthfit_user', JSON.stringify(loggedInUser));
            }

            // Sync to backend DB asynchronously
            fetch('/api/user/update-profile', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: loggedInUser.id, profile: state })
            }).catch(e => console.warn("Failed to sync profile to DB:", e));
          }
        } catch (e) {
          console.error("Member profile save failed:", e);
        }
      } else {
        // Requirement 1: 일회성(미가입회원) 진단의 경우에는 정보 기억하지 않기
        // Save strictly in transient sessionStorage; purge localStorage
        try {
          sessionStorage.setItem('youthfit_transient_profile', JSON.stringify(state));
          localStorage.removeItem('youthfit_profile');
        } catch (e) {
          console.error("Guest transient save failed:", e);
        }
      }
      window.location.href = 'loading.html';
    });
  }
});

