function initChat(username, channelId) {
    const socket = io();

    socket.on('connect', () => {
        socket.emit('join', { room: channelId });
    });

    const form = document.getElementById('message-form');
    const input = document.getElementById('message_input');
    const messages = document.getElementById('messages');

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        if (input.value) {
            socket.emit('message', {
                room: channelId,
                message: input.value
            });
            input.value = '';
        }
    });

    socket.on('message', (data) => {
        const item = document.createElement('li');
        item.textContent = `${data.username}: ${data.msg}`;
        if (data.username === username) {
            item.classList.add('my-message');
        } else {
            item.classList.add('other-message');
        }
        messages.appendChild(item);
        window.scrollTo(0, document.body.scrollHeight);
    });

    socket.on('status', (data) => {
        const item = document.createElement('li');
        item.textContent = data.msg;
        item.classList.add('status');
        messages.appendChild(item);
        window.scrollTo(0, document.body.scrollHeight);
    });

    socket.on('error', (data) => {
        alert(data.msg);
        window.location.href = '/lobby';
    });
}
