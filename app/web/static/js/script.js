/*
Author       : Dreamstechnologies
Template Name: DreamsEMR - Bootstrap Admin Template
*/

(function () {
    "use strict";

	const $wrapper = $('.main-wrapper');
	const $overlay = $('<div class="sidebar-overlay"></div>');
	$overlay.insertBefore('.main-wrapper');

	// Toggle Mobile Menu
	$(document).on('click', '#mobile_btn', function (e) {
		e.preventDefault();
		$wrapper.toggleClass('slide-nav');
		$overlay.toggleClass('opened');
		$('html').toggleClass('menu-opened');
	});

	// Close sidebar on close button click
	$(document).on('click', '.sidebar-close, .sidebar-overlay', function () {
		$wrapper.removeClass('slide-nav');
		$overlay.removeClass('opened');
		$('html').removeClass('menu-opened');
	});

	// Sidebar
	function initSidebarMenu() {
		const $menuLinks = $('.sidebar-menu a');

		$menuLinks.on('click', function (e) {
			const $link = $(this);
			const $submenu = $link.next('ul');

			if ($link.parent().hasClass('submenu')) {
				e.preventDefault();

				if (!$link.hasClass('subdrop')) {
					// Collapse all sibling submenus
					$link.closest('ul').find('ul').slideUp(250);
					$link.closest('ul').find('a').removeClass('subdrop');

					// Expand current
					$submenu.slideDown(350);
					$link.addClass('subdrop');
				} else {
					// Collapse current
					$link.removeClass('subdrop');
					$submenu.slideUp(350);
				}
			}
		});

		// Expand parent menus if active link is inside
		$('.sidebar-menu ul li.submenu a.active').parents('li.submenu').children('a').addClass('active subdrop').next('ul').show();
	}

	// Initialize Sidebar
	initSidebarMenu();

	// Mouse Over
	$(document).on('mouseover', function(e) {
        e.stopPropagation();
        if ($('body').hasClass('mini-sidebar') && $('#toggle_btn').is(':visible')) {
            var targ = $(e.target).closest('.sidebar, .header-left').length;
            if (targ) {
               	$('body').addClass('expand-menu');
                $('.subdrop + ul').slideDown();
            } else {
               	$('body').removeClass('expand-menu');
                $('.subdrop + ul').slideUp();
            }
            return false;
        }
    });

	// Toggle Button
	$(document).on('click', '#toggle_btn', function () {
		const $body = $('body');
		const $html = $('html');
		const isMini = $body.hasClass('mini-sidebar');
		const isFullWidth = $html.attr('data-layout') === 'full-width';
		const isHidden = $html.attr('data-layout') === 'hidden';

		if (isMini) {
			$body.removeClass('mini-sidebar');
			$(this).addClass('active');
			localStorage.setItem('screenModeNightTokenState', 'night');
			setTimeout(function () {
				$(".header-left").addClass("active");
			}, 100);
		} else {
			$body.addClass('mini-sidebar');
			$(this).removeClass('active');
			localStorage.removeItem('screenModeNightTokenState');
			setTimeout(function () {
				$(".header-left").removeClass("active");
			}, 100);
		}

		// If <html> has data-layout="full-width", apply full-width class to <body>
		if (isFullWidth) {
			$body.addClass('full-width').removeClass('mini-sidebar');
			$('.sidebar-overlay').addClass('opened');
			$(document).on('click', '.sidebar-close', function () {
				$('body').removeClass('full-width');
			});
		} else {
			$body.removeClass('full-width');
		}

		// If <html> has data-layout="hidden", apply hidden-layout class to <body>
		if (isHidden) {
			$body.toggleClass('hidden-layout');
			$body.removeClass('mini-sidebar');
			$(document).on('click', '.sidebar-close', function () {
				$('body').removeClass('full-width');
			});
		}

		return false;
	});

	// Tooltip
	const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
	const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

	// Input Mask
	document.querySelectorAll('[data-toggle="input-mask"]').forEach(input => {
		const format = input.getAttribute('data-mask-format');
		const reverse = input.getAttribute('data-reverse') === 'true';
		if (format && typeof Inputmask !== 'undefined') {
			Inputmask({
				mask: format.replace(/0/g, '9'),
				reverse: reverse
			}).mask(input);
		}
	});

	// Form Validation
	document.querySelectorAll('.needs-validation').forEach(form => {
		form.addEventListener('submit', event => {
			if (!form.checkValidity()) {
				event.preventDefault();
				event.stopPropagation();
			}
			form.classList.add('was-validated');
		}, false);
	});

	// Toggle Button
	$(document).on('click', '#toggle_btn2', function () {
		const $body = $('body');
		const $html = $('html');
		const isMini = $body.hasClass('mini-sidebar');
		const isFullWidth = $html.attr('data-layout') === 'full-width';
		const isHidden = $html.attr('data-layout') === 'hidden';

		if (isMini) {
			$body.removeClass('mini-sidebar');
			$(this).addClass('active');
			localStorage.setItem('screenModeNightTokenState', 'night');
			setTimeout(function () {
				$(".header-left").addClass("active");
			}, 100);
		} else {
			$body.addClass('mini-sidebar');
			$(this).removeClass('active');
			localStorage.removeItem('screenModeNightTokenState');
			setTimeout(function () {
				$(".header-left").removeClass("active");
			}, 100);
		}
		if (isFullWidth) {
			$body.addClass('full-width').removeClass('mini-sidebar');
			$('.sidebar-overlay').addClass('opened');
			$(document).on('click', '.sidebar-close', function () {
				$('body').removeClass('full-width');
			});
		} else {
			$body.removeClass('full-width');
		}
		if (isHidden) {
			$body.toggleClass('hidden-layout');
			$body.removeClass('mini-sidebar');
			$(document).on('click', '.sidebar-close', function () {
				$('body').removeClass('full-width');
			});
		}
		return false;
	});

	// Choices
	function initChoices() {
		document.querySelectorAll('[data-choices]').forEach(item => {
			const config = {
				allowHTML: true
			};
			const attrs = item.attributes;
			if (attrs['data-choices-groups']) {
				config.placeholderValue = 'This is a placeholder set in the config';
			}
			if (attrs['data-choices-search-false']) {
				config.searchEnabled = false;
			}
			if (attrs['data-choices-search-true']) {
				config.searchEnabled = true;
			}
			if (attrs['data-choices-removeItem']) {
				config.removeItemButton = true;
			}
			if (attrs['data-choices-sorting-false']) {
				config.shouldSort = false;
			}
			if (attrs['data-choices-sorting-true']) {
				config.shouldSort = true;
			}
			if (attrs['data-choices-multiple-remove']) {
				config.removeItemButton = true;
			}
			if (attrs['data-choices-limit']) {
				config.maxItemCount = parseInt(attrs['data-choices-limit'].value);
			}
			if (attrs['data-choices-editItem-true']) {
				config.editItems = true;
			}
			if (attrs['data-choices-editItem-false']) {
				config.editItems = false;
			}
			if (attrs['data-choices-text-unique-true']) {
				config.duplicateItemsAllowed = false;
			}
			if (attrs['data-choices-text-disabled-true']) {
				config.addItems = false;
			}
			const instance = new Choices(item, config);
			if (attrs['data-choices-text-disabled-true']) {
				instance.disable();
			}
		});
	}

	// Call it when the DOM is ready
	document.addEventListener('DOMContentLoaded', initChoices);

	// Initialize Flatpickr on elements with data-provider="flatpickr"
	document.querySelectorAll('[data-provider="flatpickr"]').forEach(el => {
		const config = {
			disableMobile: true
		};
		if (el.hasAttribute('data-date-format')) {
			config.dateFormat = el.getAttribute('data-date-format');
		}
		if (el.hasAttribute('data-enable-time')) {
			config.enableTime = true;
			config.dateFormat = config.dateFormat ? `${config.dateFormat} H:i` : 'Y-m-d H:i';
		}
		if (el.hasAttribute('data-altFormat')) {
			config.altInput = true;
			config.altFormat = el.getAttribute('data-altFormat');
		}
		if (el.hasAttribute('data-minDate')) {
			config.minDate = el.getAttribute('data-minDate');
		}
		if (el.hasAttribute('data-maxDate')) {
			config.maxDate = el.getAttribute('data-maxDate');
		}
		if (el.hasAttribute('data-default-date')) {
			config.defaultDate = el.getAttribute('data-default-date');
		}
		if (el.hasAttribute('data-multiple-date')) {
			config.mode = 'multiple';
		}
		if (el.hasAttribute('data-range-date')) {
			config.mode = 'range';
		}
		if (el.hasAttribute('data-inline-date')) {
			config.inline = true;
			config.defaultDate = el.getAttribute('data-inline-date');
		}
		if (el.hasAttribute('data-disable-date')) {
			config.disable = el.getAttribute('data-disable-date').split(',');
		}
		if (el.hasAttribute('data-week-number')) {
			config.weekNumbers = true;
		}
		flatpickr(el, config);
	});

	// Time Picker
	document.querySelectorAll('[data-provider="timepickr"]').forEach(item => {
		const attrs = item.attributes;
		const config = {
			enableTime: true,
			noCalendar: true,
			dateFormat: "H:i"
		};
		if (attrs["data-time-hrs"]) {
			config.time_24hr = true;
		}
		if (attrs["data-min-time"]) {
			config.minTime = attrs["data-min-time"].value;
		}
		if (attrs["data-max-time"]) {
			config.maxTime = attrs["data-max-time"].value;
		}
		if (attrs["data-default-time"]) {
			config.defaultDate = attrs["data-default-time"].value;
		}
		if (attrs["data-time-inline"]) {
			config.inline = true;
			config.defaultDate = attrs["data-time-inline"].value;
		}
		flatpickr(item, config);
	});

	// Select2
	if ($('[data-toggle="select2"]').length > 0) {
		$('[data-toggle="select2"]').each(function () {
			const $el = $(this);
			const options = {};
			// Placeholder
			if ($el.attr('data-placeholder')) {
				options.placeholder = $el.attr('data-placeholder');
			}

			// Allow clear
			if ($el.attr('data-allow-clear') === 'true') {
				options.allowClear = true;
			}

			// Tags input (user can enter new values)
			if ($el.attr('data-tags') === 'true') {
				options.tags = true;
			}

			// Maximum selection
			if ($el.attr('data-max-selections')) {
				options.maximumSelectionLength = parseInt($el.attr('data-max-selections'));
			}

			// AJAX (for dynamic search)
			if ($el.attr('data-ajax--url')) {
				options.ajax = {
					url: $el.attr('data-ajax--url'),
					dataType: 'json',
					delay: 250,
					data: function (params) {
						return {
							q: params.term, // search term
							page: params.page || 1
						};
					},
					processResults: function (data, params) {
						params.page = params.page || 1;
						return {
							results: data.items || [],
							pagination: {
								more: data.more
							}
						};
					},
					cache: true
				};
			}

			// Init Select2 with options
			$el.select2(options);
		});
	}

	// Select 2
    if ($('.select').length > 0) {
        $('.select').select2({
            minimumResultsForSearch: -1,
			dropdownParent: $('#add_test_modal'),
            width: '100%'
        });
    }

	// Popover
	const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]')
	const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl))

	//Toasts
	document.addEventListener('DOMContentLoaded', function () {
		const toastPlacement = document.getElementById('toastPlacement');
		const placementSelect = document.getElementById('selectToastPlacement');
		if (toastPlacement && placementSelect) {
			const originalClass = toastPlacement.className;
			placementSelect.addEventListener('change', function () {
			toastPlacement.className = `${originalClass} ${this.value}`.trim();
			});
		}
	});

	// Datatable
	if($('.datatable').length > 0) {
		$('.datatable').DataTable({
			"bFilter": true,
			"sDom": 'fBtlpi',
			"ordering": true,
			"language": {
				search: ' ',
				searchPlaceholder: "Search",
				sLengthMenu: 'Showing _MENU_ Results',
				info: "_START_ - _END_ of _TOTAL_ items",
				paginate: {
					next: 'Next',
					previous: 'Prev'
				},
			},
			"responsive": true,
			"autoWidth": false,
			initComplete: (settings, json)=>{
				$('.dataTables_filter').appendTo('#tableSearch');
				$('.dataTables_filter').appendTo('.search-input');
			},
		});
	}

	// Add Patient
	if ($('.patient-add').length > 0) {
		const tabMap = {
			info: '#v-pills-info',
			vitals: '#v-pills-vituals',
			medical: '#v-pills-medical-history',
			complaints: '#v-pills-complaints'
		};

		const tabBtnMap = {
			info: '#v-pills-info-tab',
			vitals: '#v-pills-vituals-tab',
			medical: '#v-pills-medical-history-tab',
			complaints: '#v-pills-complaints-tab'
		};

		// Helper to switch tabs
		const switchTab = (current, next) => {
			$(tabMap[current]).removeClass('active');
			$(tabMap[next]).addClass('active');

			$(tabBtnMap[current]).removeClass('active').addClass('activated');
			$(tabBtnMap[next]).addClass('active');
		};

		// Event Listeners
		$('#save-basic-info').on('click', () => switchTab('info', 'vitals'));
		$('#save-vitals').on('click', () => switchTab('vitals', 'medical'));
		$('#save-medical-history').on('click', () => switchTab('medical', 'complaints'));

		$('#backButton').on('click', () => {
			$(tabMap.medical).addClass('active');
			$(tabMap.complaints).removeClass('active');

			$(tabBtnMap.medical).addClass('active').removeClass('activated');
			$(tabBtnMap.complaints).removeClass('active');
		});
	}
	$(".tab-links li").on('click', function() {
	    $(this).addClass("active").siblings().removeClass('active');
	});

	// Add Doctor
	if ($('.doctor-add').length > 0) {
		const tabMap = {
			info: '#v-pills-info',
			vitals: '#v-pills-vituals',
			complaints: '#v-pills-complaints'
		};
		const tabBtnMap = {
			info: '#v-pills-info-tab',
			vitals: '#v-pills-vituals-tab',
			complaints: '#v-pills-complaints-tab'
		};

		// Tab switch helper
		const switchTab = (current, next) => {
			$(tabMap[current]).removeClass('active');
			$(tabMap[next]).addClass('active');
			$(tabBtnMap[current]).removeClass('active').addClass('activated');
			$(tabBtnMap[next]).addClass('active');
		};

		// Events
		$('#save-basic-info').on('click', () => switchTab('info', 'vitals'));
		$('#save-vitals').on('click', () => switchTab('vitals', 'complaints'));

		$('#backButton').on('click', () => {
			$(tabMap.vitals).addClass('active');
			$(tabMap.complaints).removeClass('active');
			$(tabBtnMap.vitals).addClass('active').removeClass('activated');
			$(tabBtnMap.complaints).removeClass('active');
		});
	}

	// Staff wizard
	if ($('#staff-page').length > 0) {
		const handleStaffTabs = function (config) {
			const { saveBtn, backBtn, tabOne, tabTwo, contentOne, contentTwo } = config;

			$(saveBtn).on('click', function () {
				$(contentOne).removeClass('active');
				$(contentTwo).addClass('active');
				$(tabOne).removeClass('active').addClass('activated');
				$(tabTwo).addClass('active');
			});
			$(backBtn).on('click', function () {
				$(contentTwo).removeClass('active');
				$(contentOne).addClass('active');
				$(tabTwo).removeClass('active');
				$(tabOne).addClass('active');
			});
			$(tabOne).on('click', function () {
				$(contentTwo).removeClass('active');
				$(contentOne).addClass('active');
				$(tabTwo).removeClass('active');
				$(this).addClass('active');
			});
			$(tabTwo).on('click', function () {
				$(contentOne).removeClass('active');
				$(contentTwo).addClass('active');
				$(tabOne).removeClass('active').addClass('activated');
				$(this).addClass('active');
			});
		};

		// Initialize first tab group
		handleStaffTabs({
			saveBtn: '#save-staff-info',
			backBtn: '#backButton',
			tabOne: '#staff-tab-one',
			tabTwo: '#staff-tab-two',
			contentOne: '#staff-tab-Content-one',
			contentTwo: '#staff-tab-Content-two'
		});

		// Initialize second tab group
		handleStaffTabs({
			saveBtn: '#save-staff-info-1',
			backBtn: '#backButton-1',
			tabOne: '#staff-tab-one-1',
			tabTwo: '#staff-tab-two-1',
			contentOne: '#staff-tab-Content-one-1',
			contentTwo: '#staff-tab-Content-two-1'
		});
	}

	// Active state for list items inside tab-links
	$('.tab-links li').on('click', function () {
		$(this).addClass('active').siblings().removeClass('active');
	});

	// Add Education
	$(".add-education-details").on('click', function () {

		const $servicecontent = `
		<div class="row diagnosis_details">
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Institute Name<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Qualification<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-4 col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">Year<span class="text-danger ms-1">*</span></label>
					<div class="input-group w-auto input-group-flat">
						<input type="text" class="form-control" data-provider="flatpickr" data-date-format="d M, Y">
						<span class="input-group-text">
							<i class="ti ti-calendar"></i>
						</span>
					</div>
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
            document.querySelectorAll('[data-provider="flatpickr"]').forEach(el => {
				const config = {
					disableMobile: true
				};
				if (el.hasAttribute('data-date-format')) {
					config.dateFormat = el.getAttribute('data-date-format');
				}
				flatpickr(el, config);
			});
        }, 100);
		$(".diagnosis-info > div:last-child").after($servicecontent);
		return false;
	});
	$(document).on('click', '.trash-icon', function () {
		$(this).closest('.diagnosis_details').remove();
		return false;
    });

	// Add Exp
	$(".add-experience").on('click', function () {

		const $servicecontent = `
		<div class="row experience_details">
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Hospital Name<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">No of Years<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-4 col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">Year<span class="text-danger ms-1">*</span></label>
					<div class="input-group w-auto input-group-flat">
						<input type="text" class="form-control" data-provider="flatpickr" data-date-format="d M, Y">
						<span class="input-group-text">
							<i class="ti ti-calendar"></i>
						</span>
					</div>
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
			document.querySelectorAll('[data-provider="flatpickr"]').forEach(el => {
				const config = {
					disableMobile: true
				};
				if (el.hasAttribute('data-date-format')) {
					config.dateFormat = el.getAttribute('data-date-format');
				}
				flatpickr(el, config);
			});
		}, 100);

		$(".experience-info").after($servicecontent);
		return false;
	});

	$(document).on('click', '.trash-icon', function () {
		$(this).closest('.experience_details').remove();
		return false;
    });

	// Add Membership
	$(".add-membership").on('click', function () {

		const $servicecontent = `
		<div class="row membership_details">
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Title<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Year<span class="text-danger ms-1">*</span></label>
					<div class="input-group w-auto input-group-flat">
						<input type="text" class="form-control" data-provider="flatpickr" data-date-format="d M, Y">
						<span class="input-group-text">
							<i class="ti ti-calendar"></i>
						</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">Description<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
			document.querySelectorAll('[data-provider="flatpickr"]').forEach(el => {
				const config = {
					disableMobile: true
				};
				if (el.hasAttribute('data-date-format')) {
					config.dateFormat = el.getAttribute('data-date-format');
				}
				flatpickr(el, config);
			});
		}, 100);
		$(".membership-info").after($servicecontent);
		return false;
	});

	// Membership Trash
	$(document).on('click', '.trash-icon', function () {
		$(this).closest('.membership_details').remove();
		return false;
    });

	// Add Awards
	$(".add-awards").on('click', function () {

		const $servicecontent = `
		<div class="row awards_details">
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Award Name<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Year<span class="text-danger ms-1">*</span></label>
					<div class="input-group w-auto input-group-flat">
						<input type="text" class="form-control" data-provider="flatpickr" data-date-format="d M, Y">
						<span class="input-group-text">
							<i class="ti ti-calendar"></i>
						</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">Description<span class="text-danger ms-1">*</span></label>
					<input type="text" class="form-control">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
			document.querySelectorAll('[data-provider="flatpickr"]').forEach(el => {
				const config = {
					disableMobile: true
				};
				if (el.hasAttribute('data-date-format')) {
					config.dateFormat = el.getAttribute('data-date-format');
				}
				flatpickr(el, config);
				});
			}, 100);

		$(".awards-info").after($servicecontent);
		return false;
	});
	$(document).on('click', '.trash-icon', function () {
		$(this).closest('.awards_details').remove();
		return false;
    });

	// add medicine
	$(".add-medicine").on('click', function () {

		const $servicecontent = `
		<div class="row medicine_details">
			<div class="col-xl-2 col-md-4 col-sm-6">
				<div class="mb-3">
					<label class="form-label">Medicine Name<span class="text-danger ms-1">*</span></label>
					<input class="form-control">
				</div>
			</div>
			<div class="col-xl-2 col-md-4 col-sm-6">
				<div class="mb-3">
					<label class="form-label">Dosage<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">mg</span>
					</div>
				</div>
			</div>
			<div class="col-xl-2 col-md-4 col-sm-6">
				<div class="mb-3">
					<label class="form-label">Duration<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">M</span>
					</div>
				</div>
			</div>
			<div class="col-xl-2 col-md-4 col-sm-6">
				<div class="mb-3">
					<label class="form-label">Frequency<span class="text-danger ms-1">*</span></label>
					<select class="select">
						<option>Select</option>
						<option>1-0-1</option>
						<option>1-0-0</option>
						<option>0-0-1</option>
					</select>
				</div>
			</div>
			<div class="col-xl-2 col-md-4 col-sm-6">
				<div class="mb-3">
					<label class="form-label">Timing<span class="text-danger ms-1">*</span></label>
					<select class="select">
						<option>Select</option>
						<option>Before Meal</option>
						<option>After Meal</option>
					</select>
				</div>
			</div>
			<div class="col-xl-2 col-md-4 col-sm-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">Instructions<span class="text-danger ms-1">*</span></label>
					<input class="form-control">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
            $('.select');
            setTimeout(function () {
                $('.select').select2({
                    minimumResultsForSearch: -1,
                    width: '100%'
                });
            }, 100);
        }, 100);

		$(".medicine-info > div:last-child").after($servicecontent);
		return false;
	});

	// Medicine Trash
	$(document).on('click', '.trash-icon', function () {
		$(this).closest('.medicine_details').remove();
		return false;
    });

	// Add Diagnosis
	$(".add-diagnosis-two").on('click', function () {

		const $servicecontent = `
		<div class="row diagnosis-two_details align-items-center">
			<div class="col-md-2">
				<div class="mb-md-3">
					<label class="form-label mb-md-0">Fever</label>
				</div>
			</div>
			<div class="col-md-5">
				<div class="mb-3">
					<select class="select">
						<option>Diagonosis Type</option>
						<option>Hectic</option>
						<option>Continuous Fever</option>
						<option>Relapsing</option>
					</select>
				</div>
			</div>
			<div class="col-md-5 d-flex align-items-end">
				<div class="mb-3 w-100">
					<input type="text" class="form-control" placeholder="Complaint History ( Enter Min 400 Words)">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
            $('.select');
            setTimeout(function () {
                $('.select').select2({
                    minimumResultsForSearch: -1,
                    width: '100%'
                });
            }, 100);
        }, 100);

		$(".diagnosis-two-info > div:last-child").after($servicecontent);
		return false;
	});

	// Close Diagnosis
	$(".diagnosis-two-info").on('click','.trash-icon', function () {
		$(this).closest('.diagnosis-two_details').remove();
		return false;
    });

	// Add Investigations
	$(".add-investigations").on('click', function () {
		const $servicecontent = `
		<div class="row investigations_details align-items-center">
			<div class="col-md-12 d-flex align-items-end">
				<div class="mb-3 w-100">
					<input type="text" class="form-control">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		$(".investigations-info > div:last-child").after($servicecontent);
		return false;
	});

	// Investigation Trash
	$(".investigations-info").on('click','.trash-icon', function () {
		$(this).closest('.investigations_details').remove();
		return false;
    });

	// Add Advice
	$(".add-advice").on('click', function () {
		const $servicecontent = `
		<div class="row advice_details align-items-center">
			<div class="col-md-12 d-flex align-items-end">
				<div class="mb-3 w-100">
					<input type="text" class="form-control">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		$(".advice-info > div:last-child").after($servicecontent);
		return false;
	});

	// Advice Trash
	$(".advice-info").on('click','.trash-icon', function () {
		$(this).closest('.advice_details').remove();
		return false;
    });

	// Add Follow
	$(".add-follow").on('click', function () {

		const $servicecontent = `
		<div class="row follow_details align-items-center">
		    <div class="col-md-12">
				<hr class="mt-0 mb-3">
			</div>
			<div class="col-md-6">
				<div class="mb-md-3">
					<label class="form-label mb-md-0">Next Consultation</label>
				</div>
			</div>
			<div class="col-md-6">
				<div class="mb-3">
					<select class="select">
						<option>Select</option>
						<option>Yes</option>
						<option>No</option>
					</select>
				</div>
			</div>
			<div class="col-md-6">
				<div class="mb-md-3">
					<label class="form-label mb-md-0">Whether to come on empty Stomach?</label>
				</div>
			</div>
			<div class="col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<select class="select">
						<option>Select</option>
						<option>Yes</option>
						<option>No</option>
					</select>
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
            $('.select');
            setTimeout(function () {
                $('.select').select2({
                    minimumResultsForSearch: -1,
                    width: '100%'
                });
            }, 100);
        }, 100);

		$(".follow-info > div:last-child").after($servicecontent);
		return false;
	});
	$(".follow-info").on('click','.trash-icon', function () {
		$(this).closest('.follow_details').remove();
		return false;
    });

	// Add Invoice
	$(".add-invoice").on('click', function () {

		const $servicecontent = `
		<div class="row invoice_details align-items-center">
			<div class="col-md-12 d-flex align-items-end">
				<div class="mb-3 w-100">
					<input type="text" class="form-control">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		setTimeout(function () {
            $('.select');
            setTimeout(function () {
                $('.select').select2({
                    minimumResultsForSearch: -1,
                    width: '100%'
                });
            }, 100);
        }, 100);

		$(".invoice-info > div:last-child").after($servicecontent);
		return false;
	});

	// Invoice Trash
	$(".invoice-info").on('click','.trash-icon', function () {
		$(this).closest('.invoice_details').remove();
		return false;
    });

	// Add Vitals
	$(".add-vitals").on('click', function () {

		const $servicecontent = `
		<div class="row vitals_details">
			<div class="col-12">
		       <hr class="mt-0">
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Temprature<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">F</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Pulse<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">mmHg</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Respiratory Rate<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">rpm</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">SPO2<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">%</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Height<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">cm</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Weight<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">Kg</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">BMI<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">kg/cm</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6">
				<div class="mb-3">
					<label class="form-label">Waist<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">cm</span>
					</div>
				</div>
			</div>
			<div class="col-xl-4 col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">BSA<span class="text-danger ms-1">*</span></label>
					<div class="input-group">
						<input type="text" class="form-control">
						<span class="input-group-text">M</span>
					</div>
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		$(".vitals-info > div:last-child").after($servicecontent);
		return false;
	});
	$(".vitals-info").on('click','.trash-icon', function () {
		$(this).closest('.vitals_details').remove();
		return false;
    });

	// Add Complaint
	$(".add-complaint").on('click', function () {

		const $servicecontent = `
		<div class="row complaint_details align-items-center">
		    <div class="col-12">
		       <hr class="mt-0">
			</div>
			<div class="col-md-2">
				<div class="mb-md-3">
					<label class="form-label mb-md-0">Fever</label>
				</div>
			</div>
			<div class="col-md-10 d-flex align-items-end">
				<div class="mb-3 w-100">
					<input type="text" class="form-control" placeholder="Add Symptoms">
				</div>
				<a href="javascript:void(0);" class="text-danger ms-2 mb-4 d-flex align-items-center trash-icon rounded-circle bg-soft-danger p-1"><i class="ti ti-trash fs-12"></i></a>
			</div>
		</div>`;

		$(".complaint-info > div:last-child").after($servicecontent);
		return false;
	});
	$(".complaint-info").on('click','.trash-icon', function () {
		$(this).closest('.complaint_details').remove();
		return false;
    });

	// Add New Scedule
    $(document).on('click', '.add-schedule-btn', function (e) {
    	e.preventDefault();

    	const newComplaint = `
        <div class="add-schedule-list mt-3 mt-lg-0">
            <div class="row gx-3 align-items-center">
                <div class="col-lg-8">
                    <div class="row gx-3">
                        <div class="col-lg-6">
                            <div class="mb-3">
                                <label class="form-label">From</label>
                                <div class="input-icon-end position-relative">
                                    <input type="text" class="form-control timepicker-input" placeholder="-- : -- : --">
                                    <span class="input-icon-addon">
                                        <i class="ti ti-clock-hour-10 text-dark"></i>
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="mb-3">
                                <label class="form-label">To</label>
                                <div class="input-icon-end position-relative">
                                    <input type="text" class="form-control timepicker-input" placeholder="-- : -- : --">
                                    <span class="input-icon-addon">
                                        <i class="ti ti-clock-hour-10 text-dark"></i>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4 d-flex align-items-center">
                    <div class="form-check form-switch w-100">
                        <input class="form-check-input" type="checkbox" role="switch">
                        <label class="form-check-label">Online Bookings</label>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <a href="#" class="btn p-1 remove-schedule-btn bg-soft-danger btn-icon btn-sm text-danger rounded-circle d-flex align-items-center justify-content-center">
                            <i class="ti ti-trash fs-16"></i>
                        </a>
                    </div>
                </div>
            </div>
        </div>`;

		// Insert after current one
		const $newItem = $(newComplaint);
		$(this).closest('.add-schedule-list').after($newItem);

		// Initialize timepickr (flatpickr or similar)
		$newItem.find('.timepicker-input').each(function () {
			flatpickr(this, {
				enableTime: true,
				noCalendar: true,
				dateFormat: "H:i",
				time_24hr: true
			});
		});
	});

    // Remove Scedule
    $(document).on('click', '.remove-schedule-btn', function (e) {
        e.preventDefault();
        $(this).closest('.add-schedule-list').remove();
    });

	// Awards Slider
	if($('.awards-slider').length > 0) {
		$('.awards-slider').slick({
			infinite: true,
			slidesToShow: 2,
			slidesToScroll: 1,
			responsive: [
				{
					breakpoint: 576,
					settings: {
						slidesToShow: 1,
					}
				},
			]
		});
	}

	// Visit Slider
	$('#view_modal .visit-slider').on('shown.bs.modal', function () {
		const $slider = $(this).find('.visit-slider');
		if (!$slider.hasClass('slick-initialized')) {
			$slider.slick({
				infinite: false,
				slidesToShow: 1,
				slidesToScroll: 1,
			});
		} else {
			$slider.slick('setPosition');
		}
	});

	// All Booking Calendar
	if ($('#calendar-appointment').length > 0) {
		document.addEventListener('DOMContentLoaded', function () {
			const calendarEl = document.getElementById('calendar-appointment');
			const calendar = new FullCalendar.Calendar(calendarEl, {
				initialView: 'dayGridMonth',
				headerToolbar: {
					start: 'title',
					end: 'prev,today,next'
				},
				events: [
					{
						title: '',
						images: [
							{ url: 'assets/img/users/user-01.jpg', data: 'James Carter - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-02.jpg', data: 'Sophia Wilson - 10:30 AM to 11:30 AM' }
						],
						backgroundColor: 'rgba(0, 0, 0, .2)',
						start: new Date(Date.now() - 168000000).toISOString().slice(0, 10)
					},
					{
						title: '',
						images: [
							{ url: 'assets/img/users/user-03.jpg', data: 'Thomas - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-04.jpg', data: 'Shaver - 10:30 AM to 11:30 AM' },
							{ url: 'assets/img/users/user-05.jpg', data: 'Ann - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-06.jpg', data: 'Claffin - 11:00 AM to 12:00 PM' },
							{ url: 'assets/img/users/user-07.jpg', data: 'Enrique - 12:30 PM to 01:30 PM' }
						],
						backgroundColor: 'rgba(0, 0, 0, .2)',
						start: new Date(Date.now() + 338000000).toISOString().slice(0, 10)
					},
					{
						title: '',
						images: [
							{ url: 'assets/img/users/user-08.jpg', data: 'David Smith - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-09.jpg', data: 'Deacon - 10:30 AM to 11:30 AM' },
							{ url: 'assets/img/users/user-10.jpg', data: 'Stone - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-11.jpg', data: 'Evans - 11:00 AM to 12:00 PM' }
						],
						backgroundColor: 'rgba(0, 0, 0, .2)',
						start: new Date(Date.now() - 338000000).toISOString().slice(0, 10)
					},
					{
						title: '',
						images: [
							{ url: 'assets/img/users/user-12.jpg', data: 'Daniel Williams - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-13.jpg', data: 'Deacon - 10:30 AM to 11:30 AM' },
							{ url: 'assets/img/users/user-14.jpg', data: 'Stone - 10:00 AM to 11:00 AM' },
							{ url: 'assets/img/users/user-15.jpg', data: 'Evans - 11:00 AM to 12:00 PM' }
						],
						backgroundColor: 'rgba(0, 0, 0, .2)',
						start: new Date(Date.now() + 68000000).toISOString().slice(0, 10)
					}
				],
				eventDidMount: function (info) {
					const eventEl = info.el;
					const images = info.event.extendedProps.images || [];

					// Background color on day cell
					const tdEl = eventEl.closest('td');
					if (tdEl) tdEl.style.backgroundColor = info.event.backgroundColor;

					// Prepare image avatars
					const avatarImages = images.slice(0, 2).map(img => `
						<img class="fc-event-image avatar avatar-sm rounded-circle calendar-img"
							src="${img.url}" alt="" title="${img.data}" data-bs-toggle="tooltip" data-bs-placement="top">
					`).join('');

					const moreImages = images.slice(2);
					const moreImagesHtml = moreImages.map(img => `
						<div class="d-flex align-items-center avatar avatar-sm rounded-circle cal-img">
							<img class="fc-event-image calendar-img" src="${img.url}" alt="${img.data}"
								title="${img.data}" data-bs-toggle="tooltip" style="display:none;">
						</div>
					`).join('');

					// Build 'Show more' popover content
					let showMoreLink = '';
					let popover = null;

					if (moreImages.length > 0) {
						showMoreLink = `<a href="javascript:void(0);" class="show-more">Show more</a>`;

						const popoverContent = `
							<div class="calendar-popover">
								<div class="calendar-popover-header d-flex justify-content-between align-items-center mb-2">
									<strong>${info.event.start.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric' })}</strong>
									<button type="button" class="btn-close popover-close" aria-label="Close"></button>
								</div>
								<div class="calendar-popover-body">
									${images.map(image => {
										const [name, time] = image.data.split('-');
										return `
											<div class="calendar-popover-item d-flex align-items-center justify-content-between mb-2">
												<div class="d-flex align-items-center">
													<img src="${image.url}" class="rounded-circle avatar avatar-sm me-2" />
													<span class="fw-medium">${name.trim()}</span>
												</div>
												<div class="text-muted small">${time?.trim() || ''}</div>
											</div>
										`;
									}).join('')}
								</div>
							</div>
						`;

						popover = new bootstrap.Popover(eventEl, {
							html: true,
							trigger: 'click',
							content: popoverContent,
							placement: 'auto',
							container: 'body'
						});

						eventEl.addEventListener('shown.bs.popover', function () {
							const popoverId = eventEl.getAttribute('aria-describedby');
							const popoverEl = document.getElementById(popoverId);
							if (popoverEl) {
								var closeBtn = popoverEl.querySelector('.popover-close');
								if (closeBtn) {
									closeBtn.addEventListener('click', function () {
										popover.hide();
									});
								}
							}
						});
					}

					// Inject avatars and optional "Show more"
					const imageWrapper = document.createElement('div');
					imageWrapper.innerHTML = avatarImages + moreImagesHtml + showMoreLink;
					const titleContainer = eventEl.querySelector('.fc-event-title-container');
					if (titleContainer) {
						titleContainer.appendChild(imageWrapper);
					}

					// Tooltip initialization for current event only
					$(eventEl).find('[data-bs-toggle="tooltip"]').tooltip();
				}
			});

			calendar.render();
		});
	}

	// Toggle Password
	if ($('.toggle-password').length > 0) {
		$(document).on('click', '.toggle-password', function () {
			const $icon = $(this).find('i');
			const $input = $(this).closest('.input-group').find('.pass-input');
			if ($input.attr('type') === 'password') {
				$input.attr('type', 'text');
				$icon.removeClass('ti-eye-off').addClass('ti-eye');
			} else {
				$input.attr('type', 'password');
				$icon.removeClass('ti-eye').addClass('ti-eye-off');
			}
		});
	}

	// year picker
	if($('.yearpicker').length > 0 ){
		$('.yearpicker').datetimepicker({
			viewMode: 'years',
			format: 'YYYY',
			icons: {
				up: "ti ti-chevron-up",
				down: "ti ti-chevron-down",
				next: 'ti ti-chevron-right',
				previous: 'ti ti-chevron-left'
			}
		});
	}

	// Add new medication input on '+' click
	$(document).on('click', '.add-medication', function (e) {
		e.preventDefault();

		const newComplaint = `
		<div class="row medication-list-item">
			<div class="col-xl-3 col-md-6">
			<div class="mb-3">
				<label class="form-label">Type</label>
				<select class="select">
					<option>Select</option>
					<option>Allergy</option>
					<option>Fever</option>
				</select>
			</div>
			</div>
			<div class="col-xl-3 col-md-6">
				<div class="mb-3">
					<label class="form-label">Date of Illness</label>
					<div class="input-group w-auto input-group-flat">
						<input type="text" class="form-control" data-provider="flatpickr" data-date-format="d M, Y">
						<span class="input-group-text">
							<i class="ti ti-calendar"></i>
						</span>
					</div>
				</div>
			</div>
			<div class="col-xl-3 col-md-6">
				<div class="mb-3">
					<label class="form-label">Reason</label>
					<input type="text" class="form-control">
				</div>
			</div>
			<div class="col-xl-3 col-md-6 d-flex align-items-end">
				<div class="mb-3 w-100">
					<label class="form-label">Hospital Name</label>
					<input type="text" class="form-control">
				</div>
				<div class="mb-3">
					<label class="form-label mb-1 text-dark fs-14 fw-medium"></label>
					<a href="#" class="remove-medication ms-2 p-2 bg-light text-danger rounded d-flex align-items-center justify-content-center"><i class="ti ti-trash fs-16"></i></a>
			    </div>
			</div>
			<div class="col-md-12">
				<div class="mb-3 border-bottom pb-2">
					<div class="form-check mb-2">
						<input type="checkbox" class="form-check-input" id="customCheck5">
						<label class="form-check-label form-label mb-0" for="customCheck5">Assessment done if any</label>
					</div>
					<div class="form-check mb-2">
						<input type="checkbox" class="form-check-input" id="customCheck6">
						<label class="form-check-label form-label mb-0" for="customCheck6">Notes</label>
					</div>
					<div class="form-check mb-2">
						<input type="checkbox" class="form-check-input" id="customCheck7">
						<label class="form-check-label form-label mb-0" for="customCheck7">Documents If any</label>
					</div>
				</div>
			</div>
		</div>`;

		setTimeout(function () {
            $('.select');
            setTimeout(function () {
                $('.select').select2({
                    minimumResultsForSearch: -1,
                    width: '100%'
                });
            }, 100);
        }, 100);

		setTimeout(function () {
			document.querySelectorAll('[data-provider="flatpickr"]').forEach(el => {
				const config = {
					disableMobile: true
				};
				if (el.hasAttribute('data-date-format')) {
					config.dateFormat = el.getAttribute('data-date-format');
				}
				flatpickr(el, config);
			});
		}, 100);

		// Insert before the add button row
		$(this).closest('.medication-list-item').before(newComplaint);
	});

	// Remove invest input on trash icon click
	$(document).on('click', '.remove-medication', function (e) {
		e.preventDefault();
		$(this).closest('.medication-list-item').remove();
	});

	// Date Range Picker
	if ($('#reportrange').length > 0) {
		const start = moment().subtract(29, "days");
		const end = moment();
		const report_range = (start, end) => {
			$("#reportrange span").html(`${start.format("D MMM YY")} - ${end.format("D MMM YY")}`);
		};
		$("#reportrange").daterangepicker(
			{
				startDate: start,
				endDate: end,
				ranges: {
					'Today': [moment(), moment()],
					'Yesterday': [moment().subtract(1, "days"), moment().subtract(1, "days")],
					"Last 7 Days": [moment().subtract(6, "days"), moment()],
					"Last 30 Days": [moment().subtract(29, "days"), moment()],
					"This Month": [moment().startOf("month"), moment().endOf("month")],
					"Last Month": [
						moment().subtract(1, "month").startOf("month"),
						moment().subtract(1, "month").endOf("month")
					]
				}
			},
			report_range
		);
		report_range(start, end);
	}

	// Custom Country Code Selector
	if ($('.phone').length) {
		document.querySelectorAll(".phone").forEach(input => {
			window.intlTelInput(input, {
				utilsScript: "assets/plugins/intltelinput/js/utils.js",
			});
		});
	}

	// Select Table Checkbox
	$('#select-all').on('change', function () {
		$('.form-check.form-check-md input[type="checkbox"]').prop('checked', this.checked);
	});

	// Full Screen
    if ($('.btnFullscreen').length) {
		const toggleFullscreen = function () {
			if (!document.fullscreenElement) {
				document.documentElement.requestFullscreen();
			} else {
				if (document.exitFullscreen) {
					document.exitFullscreen();
				}
			}
		};
		$('.btnFullscreen').on('click', toggleFullscreen);
	}

	// Aprrearence Settings
	$('.theme-image').on('click', function(){
		$('.theme-image').removeClass('active');
		$(this).addClass('active');
	});

	// Sticky Sidebar
	if ($(window).width() > 767) {
		if ($('.theiaStickySidebar').length > 0) {
			$('.theiaStickySidebar').theiaStickySidebar({
				additionalMarginTop: 30
			});
		}
	}

	// Select
	function initCheckboxGroup(groupClass, selectAllClass, checkboxClass) {
		$('.' + groupClass).each(function () {
			const $group = $(this);
			const $selectAll = $group.find('.' + selectAllClass);
			const $checkboxes = $group.find('.' + checkboxClass);

			$selectAll.on('change', function () {
				$checkboxes.prop('checked', this.checked);
			});
		});
	}

	// Initialize all groups
	initCheckboxGroup('select-group', 'selectall', 'form-check-md');
	initCheckboxGroup('select-group2', 'selectall2', 'form-check-md2');
	initCheckboxGroup('select-group3', 'selectall3', 'form-check-md3');

	// Add More rows
	document.addEventListener('DOMContentLoaded', () => {
		const tableBody = document.querySelector('#item-table tbody');
		const addButton = document.getElementById('add-item-btn');

		if (tableBody && addButton) {
			// Add more rows
			addButton.addEventListener('click', () => {
				const newRow = `
				<tr>
					<td><input type="text" class="form-control form-control-sm"></td>
					<td><input type="text" class="form-control form-control-sm" placeholder="Qty"></td>
					<td><input type="text" class="form-control form-control-sm"></td>
					<td><input type="text" class="form-control form-control-sm"></td>
					<td><input type="text" class="form-control form-control-sm"></td>
					<td><input type="text" class="form-control form-control-sm"></td>
					<td class="ps-0">
						<select class="form-select form-select-sm">
							<option value="1">%</option>
							<option value="2">$</option>
						</select>
					</td>
					<td class="text-gray-9 fw-14 fw-medium">$0.00</td>
					<td><a href="javascript:void(0);" class="delete-row link-danger"><i class="ti ti-trash"></i></a></td>
				</tr>`;
				tableBody.insertAdjacentHTML('beforeend', newRow);
			});

			// Remove row on trash icon click
			document.addEventListener('click', (e) => {
				if (e.target.closest('.delete-row')) {
					e.target.closest('tr').remove();
				}
			});
		}
	});

	// Circle Progress
	$(function() {

		$(".circle-progress").each(function() {

		  var value = $(this).attr('data-value');
		  var left = $(this).find('.progress-left .progress-bar');
		  var right = $(this).find('.progress-right .progress-bar');

		  if (value > 0) {
			if (value <= 50) {
			  right.css('transform', 'rotate(' + percentageToDegrees(value) + 'deg)')
			} else {
			  right.css('transform', 'rotate(180deg)')
			  left.css('transform', 'rotate(' + percentageToDegrees(value - 50) + 'deg)')
			}
		  }

		})

		function percentageToDegrees(percentage) {

		  return percentage / 100 * 360

		}

	});

})();
