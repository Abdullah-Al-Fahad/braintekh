# DiasporaVest / Damani AI 
## Client Setup Guide: Social Login Configuration

To enable the "Sign in with Google" and "Sign in with Apple" features in the mobile application, certain developer accounts must be configured to generate the required cryptographic keys. 

Since these accounts must be tied to your company's domain, billing, and legal entity, they cannot be created by external developers. Please follow the steps below and provide the resulting keys to your development team.

---

## Part 1: Google Cloud Setup (Sign In With Google)

You need to create a Google Cloud Project to generate the **Web Client ID**.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and log in with a company Google account.
2. Click the project dropdown at the top left and click **New Project**.
3. Name the project **Damani AI** (or similar) and click Create.
4. On the left sidebar, go to **APIs & Services** > **OAuth consent screen**.
5. Choose **External** and fill in the required App Name (Damani AI), User Support Email, and Developer Contact Information. Save and Continue.
6. Now go to **APIs & Services** > **Credentials**.
7. Click **+ Create Credentials** at the top and select **OAuth client ID**.
8. Select Application Type: **Web application**.
9. Name it: `Damani AI Web Backend Client`.
10. Click **Create**.
11. A popup will appear containing your **Client ID** (it will look like `1003008036989-xxxxxx.apps.googleusercontent.com`).

**✅ What you need to give the developer:** 
Copy the **Client ID** and provide it to the backend developer.

---

## Part 2: Apple Developer Setup (Sign In With Apple)

Apple strictly requires an active, paid Apple Developer Account to enable "Sign In with Apple".

1. Log into the [Apple Developer Portal](https://developer.apple.com/) (Requires the Account Holder or Admin role).
2. Go to **Certificates, Identifiers & Profiles**.
3. On the left sidebar, click **Identifiers**.
4. Click the blue **+** button to register a new App ID. Select **App IDs** > Continue.
5. Enter your App's Description (Damani AI) and the **Bundle ID** (`com.braintekh.diafi`). 
6. Scroll down the Capabilities list and check the box for **Sign In with Apple**. 
7. Click Continue and then Register.

Now you must generate the Private Key for the backend:
1. Still in the Developer Portal, click **Keys** on the left sidebar.
2. Click the blue **+** button to create a new key.
3. Name the key: `Damani AI Sign In with Apple Key`.
4. Check the box for **Sign in with Apple**. 
5. Click the **Configure** button on that row, select your App ID (`com.braintekh.diafi`), and click Save.
6. Click Continue and then **Register**.
7. Click the **Download** button to download the `.p8` private key file. **(Do not lose this file, you can only download it once!)**

**✅ What you need to give the developer:** 
Provide the following 3 items to your backend developer:
1. The **`.p8` file** you just downloaded.
2. Your **10-character Team ID** (Found in the top right corner under your name).
3. The **Key ID (kid)** (Found on the Key Details page right after downloading the `.p8` file).

---

Once the developers receive these keys, they will insert them into the backend configuration, and Social Login will instantly become functional on the mobile app.
