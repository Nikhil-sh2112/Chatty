document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const fileInput = document.getElementById('file-input');
    const chatContainer = document.getElementById('chat-container');
    let isProcessing = false;

    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        if (isProcessing) return;
        
        isProcessing = true;
        const submitBtn = chatForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;

        try {
            const formData = new FormData();
            const message = messageInput.value.trim();
            
            if (message) formData.append('message', message);
            if (fileInput.files[0]) {
                formData.append('file', fileInput.files[0]);
                
                // Handle conversion if specified in message
                if (message.toLowerCase().includes('convert to')) {
                    const targetFormat = message.toLowerCase().match(/convert to (\w+)/)?.[1];
                    if (targetFormat) formData.append('format', targetFormat);
                }
            }

            const response = await fetch(window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                // Add message to UI without reload
                addMessageToUI({
                    content: message || fileInput.files[0]?.name,
                    isOutgoing: true,
                    timestamp: new Date().toISOString()
                });
                
                // Clear inputs
                messageInput.value = '';
                fileInput.value = '';
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            isProcessing = false;
            submitBtn.disabled = false;
        }
    });

    // Function to add messages to UI
    function addMessageToUI(message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.isOutgoing ? 'outgoing' : 'incoming'}`;
        messageElement.innerHTML = `
            <div class="message-content">${message.content}</div>
            <div class="message-time">${new Date(message.timestamp).toLocaleTimeString()}</div>
        `;
        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Poll for new messages
    let lastMessageId = 0;
    setInterval(async () => {
        try {
            const response = await fetch(`/api/messages/${recipientId}?since=${lastMessageId}`);
            const messages = await response.json();
            
            messages.forEach(msg => {
                if (msg.id > lastMessageId) {
                    addMessageToUI({
                        content: msg.content,
                        isOutgoing: msg.sender_id === currentUserId,
                        timestamp: msg.timestamp
                    });
                    lastMessageId = msg.id;
                }
            });
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 3000);
});