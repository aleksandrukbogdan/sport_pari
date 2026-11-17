for (const node of document.querySelectorAll('time[datetime]')) {
    const date = new Date(node.dateTime);
    if (!Number.isNaN(date.valueOf())) {
        node.textContent = new Intl.DateTimeFormat('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
        node.title = 'Время в вашем часовом поясе';
    }
}
for (const image of document.querySelectorAll('img')) {
    image.addEventListener('error', () => {
        image.hidden = true;
    });
}
for (const form of document.querySelectorAll('form[data-pending]')) {
    form.addEventListener('submit', event => {
        if (form.dataset.submitting === 'true') {
            event.preventDefault();
            return;
        }
        form.dataset.submitting = 'true';
        form.setAttribute('aria-busy', 'true');
        for (const button of form.querySelectorAll('button[type="submit"]')) {
            button.dataset.originalText = button.textContent;
            button.disabled = true;
            button.textContent = form.dataset.pending;
        }
    });
}
window.addEventListener('pageshow', () => {
    for (const form of document.querySelectorAll('form[data-pending]')) {
        form.dataset.submitting = 'false';
        form.removeAttribute('aria-busy');
        for (const button of form.querySelectorAll('button[data-original-text]')) {
            button.disabled = false;
            button.textContent = button.dataset.originalText;
        }
    }
});
const comment = document.querySelector('textarea[data-draft-key]');
if (comment) {
    try {
        const key = comment.dataset.draftKey;
        if (new URLSearchParams(window.location.search).get('comment') === 'sent') sessionStorage.removeItem(key);
        else if (!comment.value) comment.value = sessionStorage.getItem(key) || '';
        comment.addEventListener('input', () => sessionStorage.setItem(key, comment.value));
    } catch {
        /* Browser storage may be disabled. The server also preserves validation errors. */ }
    const count = document.querySelector('[data-character-count]');
    const updateCount = () => {
        if (count) count.textContent = `${comment.value.length} / 2000`;
    };
    comment.addEventListener('input', updateCount);
    updateCount();
}
