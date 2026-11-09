// main.js — students will add JavaScript here as features are built

// ------------------------------------------------------------------ //
// Landing page: "See how it works" video modal                        //
// ------------------------------------------------------------------ //
(function () {
    var openBtn = document.getElementById('video-open');
    var modal = document.getElementById('video-modal');
    var closeBtn = document.getElementById('video-close');
    var iframe = document.getElementById('video-iframe');

    if (!openBtn || !modal || !closeBtn || !iframe) return;

    function openModal() {
        // Set src only on open so the video loads (and autoplays) on demand.
        iframe.src = openBtn.getAttribute('data-video-src') + '?autoplay=1&rel=0';
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
        closeBtn.focus();
    }

    function closeModal() {
        // Clearing src unloads the player, which stops the video completely.
        iframe.src = '';
        modal.hidden = true;
        document.body.style.overflow = '';
        openBtn.focus();
    }

    openBtn.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);

    // Click on the dark backdrop (but not on the dialog itself) closes it.
    modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !modal.hidden) closeModal();
    });
})();
