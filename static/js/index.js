// create send message with ticket, token
// and message
var sendMessage = function(ticket, token, _message) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://127.0.0.1:8080/' + token + '/' + ticket + '/send_message', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    var params = 'message=' + _message;
    xhr.send(params);
}

// get server timestamp
var getTimestamp = function(token) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'http://127.0.0.1:8080/' + token + '/get_timestamp', false);
    xhr.send();
    return JSON.parse(xhr.responseText).timestamp;
}

    
// polling for new messages
var poll = function(timestamp, ticket, token) {
    this.timestamp = timestamp;

    var poll_response = $.ajax({
        url: 'http://127.0.0.1:8080/' + token + '/' + ticket + '/polling/' + timestamp,
        type: 'GET',
        success: function(data) {
            this.timestamp = data.timestamp;
            appendMessage(data.messages);
            return poll(this.timestamp, ticket, token);
            // console.log(data);
        },
        // complete: function() { poll(this.timestamp, ticket, token); },
        dataType: 'json'
    });
}

// append to messages content div
var appendMessage = function(messages) {
    console.log(messages);
    for (let i = 0; i < messages.length; i++) {
        let message = messages[i];
        $('.messages').append('<div class="message-operator">\n' + 
        '<div class="message-header">\n' + 
        '<p>' + message.user_id.toString() + '</p>\n' +
        '<p>' + message.date.toString() + '</p>\n' +
        '</div>\n' +
        '<div class="message-body">\n' +
        '<p>' + message.message.toString() + '</p>\n' +
        '</div>\n' +
        '</div>\n'
        );
    }

    // scroll to bottom
    $('.messages').scrollTop($('.messages')[0].scrollHeight);
}