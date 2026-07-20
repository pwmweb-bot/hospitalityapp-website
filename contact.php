<?php
/**
 * Contact form handler for hospitalityapp.co.uk.
 * Self-contained, no dependencies. Emails enquiries to hello@ and redirects
 * back to /contact with a status. Defensive: honeypot, validation, and
 * CR/LF stripping on every header-bound value to prevent header injection.
 */

function cf_redirect($query) {
    header('Location: /contact' . $query, true, 303);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    cf_redirect('');
}

// Honeypot — bots fill this hidden field. Pretend success, drop silently.
if (!empty($_POST['company_website'])) {
    cf_redirect('?sent=1');
}

$name    = trim($_POST['name'] ?? '');
$email   = trim($_POST['email'] ?? '');
$venue   = trim($_POST['venue'] ?? '');
$phone   = trim($_POST['phone'] ?? '');
$typeKey = trim($_POST['type'] ?? 'general');
$message = trim($_POST['message'] ?? '');

// Required fields + valid email.
if ($name === '' || $message === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    cf_redirect('?error=validation');
}

// Basic length guards.
if (strlen($name) > 120 || strlen($email) > 200 || strlen($message) > 5000) {
    cf_redirect('?error=validation');
}

// Strip CR/LF from anything that touches a mail header.
$header_safe = function ($s) {
    return trim(str_replace(array("\r", "\n", "\0"), ' ', $s));
};
$name  = $header_safe($name);
$email = $header_safe($email);
$venue = $header_safe($venue);
$phone = $header_safe($phone);

// Allow-list the enquiry type by key → human label.
$types = array(
    'general'   => 'General enquiry',
    'demo'      => 'Book a demo',
    'multisite' => 'Multi-site walkthrough',
    'support'   => 'Support',
);
$type = $types[$typeKey] ?? 'General enquiry';

$to      = 'hello@hospitalityapp.co.uk';
$subject = '[Website] ' . $type . ' — ' . $name;

$body  = "New enquiry from the hospitalityapp.co.uk contact form.\n\n";
$body .= "Type:    " . $type . "\n";
$body .= "Name:    " . $name . "\n";
$body .= "Email:   " . $email . "\n";
$body .= "Venue:   " . ($venue !== '' ? $venue : '—') . "\n";
$body .= "Phone:   " . ($phone !== '' ? $phone : '—') . "\n\n";
$body .= "Message:\n" . $message . "\n";

$headers  = "From: HospitalityApp Website <noreply@hospitalityapp.co.uk>\r\n";
$headers .= "Reply-To: " . $name . " <" . $email . ">\r\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
$headers .= "X-Mailer: hospitalityapp-website\r\n";

$sent = @mail($to, $subject, $body, $headers);

cf_redirect($sent ? '?sent=1' : '?error=send');
