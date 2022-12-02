// create send message with ticket, token
// and message
var sendMessage = function(ticket, token, _message) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://127.0.0.1:8080/' + token + '/' + ticket + '/send_message', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    var params = 'message=' + _message;
    xhr.send(params);

    // clear input
    $('#message').val('');
}

var solveTicket = function(ticket, token) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'http://127.0.0.1:8080/' + token + '/' + ticket + '/close_thread', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send();

    // refresh page
    location.reload();
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
            appendMessage(data.messages, data.users);
            return poll(this.timestamp, ticket, token);
            // console.log(data);
        },
        // complete: function() { poll(this.timestamp, ticket, token); },
        dataType: 'json'
    });
}

var timestampToDate = function(timestamp) {
    var date = new Date(timestamp);
    return date.getHours() + ':' + date.getMinutes() + ':' + date.getSeconds() + ", " + date.toDateString();
}

// append to messages content div
var appendMessage = function(messages, users) {
    for (let i = 0; i < messages.length; i++) {
        let message = messages[i];
        let user = users[message.user_id];
        var date = timestampToDate(parseFloat(message.date) * 1000);
        
        if (user.is_operator) {
            $('.messages').append('<div class="message-operator">\n' + 
            '<div class="message-header">\n' + 
            '<p>' + user.telegram_username.toString() + '</p>\n' +
            '<p>' + date + '</p>\n' +
            '</div>\n' +
            '<div class="message-body">\n' +
            '<p>' + message.message.toString() + '</p>\n' +
            '</div>\n' +
            '</div>\n'
            );
        } else {
            $('.messages').append('<div class="message-user">\n' + 
            '<div class="message-header">\n' + 
            '<p>' + user.telegram_username.toString() + '</p>\n' +
            '<p>' + date + '</p>\n' +
            '</div>\n' +
            '<div class="message-body">\n' +
            '<p>' + message.message.toString() + '</p>\n' +
            '</div>\n' +
            '</div>\n'
            );
        }
    }

    // scroll to bottom
    if (messages.length > 0) {
        $('.messages').scrollTop($('.messages')[0].scrollHeight);
    }
}