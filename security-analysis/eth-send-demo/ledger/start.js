// Startseite: Email-Input → Session-Link per Email senden

const $ = (id) => document.getElementById(id);

const emailInput = $('email-input');
const sendBtn = $('send-link-btn');
const emailError = $('email-error');
const successBox = $('success-box');

// Email-Validation Regex (einfach aber effektiv)
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateEmail(email) {
  return EMAIL_REGEX.test(email);
}

function updateButtonState() {
  const email = emailInput.value.trim();
  const isValid = email.length > 0 && validateEmail(email);
  sendBtn.disabled = !isValid;
  emailInput.classList.toggle('invalid', email.length > 0 && !isValid);
  
  if (email.length > 0 && !isValid) {
    emailError.textContent = 'Please enter a valid email address';
  } else {
    emailError.textContent = '';
  }
}

emailInput.addEventListener('input', updateButtonState);
emailInput.addEventListener('blur', updateButtonState);

// Enter im Input → Button auslösen
emailInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !sendBtn.disabled) {
    sendBtn.click();
  }
});

async function sendSessionLink() {
  const email = emailInput.value.trim();
  if (!validateEmail(email)) {
    emailError.textContent = 'Please enter a valid email address';
    emailInput.classList.add('invalid');
    return;
  }

  // Loading-State
  sendBtn.disabled = true;
  sendBtn.textContent = 'Sending...';
  emailError.textContent = '';
  successBox.classList.add('hidden');

  try {
    const response = await fetch('/api/send-session-link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'Failed to send link');
    }

    // Success
    successBox.classList.remove('hidden');
    sendBtn.textContent = 'Link Sent';
    emailInput.disabled = true;

    // Optional: Nach 5 Sekunden Reset für neuen Versuch
    setTimeout(() => {
      successBox.classList.add('hidden');
      sendBtn.textContent = 'Send Verification Link';
      sendBtn.disabled = false;
      emailInput.disabled = false;
      emailInput.value = '';
      emailInput.focus();
    }, 5000);

  } catch (error) {
    // Error
    emailError.textContent = error.message || 'Failed to send link. Please try again.';
    emailInput.classList.add('invalid');
    sendBtn.textContent = 'Send Verification Link';
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener('click', sendSessionLink);

// Initial State
updateButtonState();
