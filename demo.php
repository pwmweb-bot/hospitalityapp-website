<?php
/**
 * Demo lead handler for hospitalityapp.co.uk.
 * Emails business and owner details to hello@, then returns the visitor to
 * /demo/ so they can book the shared 15-minute Calendly slot. Honeypot,
 * validation, and CR/LF stripping match contact.php.
 */

function demo_redirect($query) {
    header('Location: /demo/' . $query, true, 303);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    demo_redirect('');
}

// Honeypot — bots fill this hidden field. Pretend success, drop silently.
if (!empty($_POST['company_website'])) {
    demo_redirect('?sent=1#times');
}

$business = trim($_POST['business_name'] ?? '');
$address  = trim($_POST['business_address'] ?? '');
$bphone   = trim($_POST['business_phone'] ?? '');
$name     = trim($_POST['name'] ?? '');
$email    = trim($_POST['email'] ?? '');
$phone    = trim($_POST['phone'] ?? '');
$note     = trim($_POST['note'] ?? '');

if ($business === '' || $address === '' || $bphone === '' || $name === '' || $phone === ''
    || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    demo_redirect('?error=validation#details');
}

if (strlen($business) > 160 || strlen($address) > 400 || strlen($bphone) > 40
    || strlen($name) > 120 || strlen($email) > 200 || strlen($phone) > 40
    || strlen($note) > 2000) {
    demo_redirect('?error=validation#details');
}

$header_safe = function ($s) {
    return trim(str_replace(array("\r", "\n", "\0"), ' ', $s));
};
$note     = str_replace("\0", '', $note);
$address  = str_replace("\0", '', $address);
$business = $header_safe($business);
$bphone   = $header_safe($bphone);
$name     = $header_safe($name);
$email    = $header_safe($email);
$phone    = $header_safe($phone);

$to = 'hello@hospitalityapp.co.uk';
$mime_header = function ($s) {
    if (preg_match('/^[\x20-\x7E]*$/', $s)) { return $s; }
    return '=?UTF-8?B?' . base64_encode($s) . '?=';
};
$subject = $mime_header('[Website] 15-min demo — ' . $business);

$body  = "New 15-minute demo lead from hospitalityapp.co.uk/demo/.\n\n";
$body .= "Business:       " . $business . "\n";
$body .= "Address:        " . $address . "\n";
$body .= "Business phone: " . $bphone . "\n";
$body .= "Owner:          " . $name . "\n";
$body .= "Email:          " . $email . "\n";
$body .= "Owner phone:    " . $phone . "\n\n";
$body .= "Note:\n" . ($note !== '' ? $note : "—") . "\n";

$headers  = "From: Hospitality App Website <noreply@hospitalityapp.co.uk>\r\n";
$reply_plain = str_replace(array('\\', '"'), '', $name);
$reply_name  = preg_match('/^[\x20-\x7E]*$/', $reply_plain)
    ? '"' . $reply_plain . '"'
    : $mime_header($reply_plain);
$headers .= "Reply-To: " . $reply_name . " <" . $email . ">\r\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
$headers .= "X-Mailer: hospitalityapp-website\r\n";

$sent = @mail($to, $subject, $body, $headers);

demo_redirect($sent ? '?sent=1#times' : '?error=send#details');
