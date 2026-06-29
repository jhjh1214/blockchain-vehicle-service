package com.example.owner_mobile_app

import io.flutter.embedding.android.FlutterFragmentActivity

// local_auth's Android BiometricPrompt integration requires a FragmentActivity
// host — a plain FlutterActivity can't show the fingerprint dialog at all.
class MainActivity : FlutterFragmentActivity()
