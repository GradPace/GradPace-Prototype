// The password rules, shown under a password box. They match
// AUTH_PASSWORD_VALIDATORS in backend/config/settings/base.py.
export default function PasswordRules() {
  return (
    <ul className="-mt-4 list-disc space-y-1 pl-5 text-sm text-slate">
      <li>At least 8 characters</li>
      <li>1 uppercase letter</li>
      <li>1 number</li>
      <li>1 special character (!@#$%^&*)</li>
      <li>Not a common word or common password</li>
      <li>No repeated or sequential characters (e.g. &quot;aaaa&quot;, &quot;1234&quot;)</li>
    </ul>
  );
}
