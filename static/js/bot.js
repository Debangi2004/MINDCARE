$(document).ready(function() {
    let currentSessionId = null;
    const chatArea = $('.msger-chat');
    
    // Function to add a message to the chat
    function appendMessage(message, isUser = false) {
        const msgDiv = $('<div class="msg ' + (isUser ? 'right-msg' : 'left-msg') + '">');
        const msgImg = $('<div class="msg-img">').css('background-image', 
            isUser ? 'url(https://image.flaticon.com/icons/svg/145/145867.svg)' : 
            'url(https://image.flaticon.com/icons/svg/327/327779.svg)');
        
        const msgBubble = $('<div class="msg-bubble">');
        const msgInfo = $('<div class="msg-info">');
        const msgInfoName = $('<div class="msg-info-name">').text(isUser ? 'You' : 'Psychiatrist Bot');
        const msgInfoTime = $('<div class="msg-info-time">').text(new Date().toLocaleTimeString());
        
        msgInfo.append(msgInfoName, msgInfoTime);
        const msgText = $('<div class="msg-text">').text(message);
        msgBubble.append(msgInfo, msgText);
        msgDiv.append(msgImg, msgBubble);
        chatArea.append(msgDiv);
        
        // Scroll to bottom
        chatArea.scrollTop(chatArea[0].scrollHeight);
    }

    // Function to load chat history
    function loadChatHistory(sessionId) {
        $.get(`/history/${sessionId}`, function(history) {
            chatArea.empty(); // Clear existing messages
            history.forEach(msg => {
                appendMessage(msg.message, true);
                appendMessage(msg.response, false);
            });
        });
    }

    // Handle form submission
    $('.msger-inputarea').submit(function(e) {
        e.preventDefault();
        const userMessage = $('#textInput').val().trim();
        
        if (userMessage) {
            // Add user message to chat
            appendMessage(userMessage, true);
            
            // Clear input
            $('#textInput').val('');
            
            // Send message to server
            $.get('/get', {
                msg: userMessage,
                session_id: currentSessionId
            }, function(data) {
                // Update session ID if it's a new session
                if (!currentSessionId) {
                    currentSessionId = data.session_id;
                }
                
                // Add bot response to chat
                appendMessage(data.response, false);
            });
        }
    });

    // Toggle chat window
    $('#chatbot_toggle').click(function() {
        const chatbot = $('#chatbot');
        chatbot.toggleClass('collapsed');
        
        // Load chat history when opening chat
        if (!chatbot.hasClass('collapsed') && currentSessionId) {
            loadChatHistory(currentSessionId);
        }
    });

    // Update clock
    function updateClock() {
        $('#clock').text(new Date().toLocaleTimeString());
    }
    setInterval(updateClock, 1000);
    updateClock();
});
