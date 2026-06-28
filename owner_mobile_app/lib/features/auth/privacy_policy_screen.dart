import 'package:flutter/material.dart';

/// Displays the Privacy Policy and Terms of Service inline.
/// Can be opened from login, register, or profile screens.
class PrivacyPolicyScreen extends StatefulWidget {
  final bool showTabs;
  const PrivacyPolicyScreen({super.key, this.showTabs = true});

  @override
  State<PrivacyPolicyScreen> createState() => _PrivacyPolicyScreenState();
}

class _PrivacyPolicyScreenState extends State<PrivacyPolicyScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Legal'),
        bottom: widget.showTabs
            ? TabBar(
                controller: _tabs,
                tabs: const [
                  Tab(text: 'Privacy Policy'),
                  Tab(text: 'Terms of Service'),
                ],
              )
            : null,
      ),
      body: widget.showTabs
          ? TabBarView(
              controller: _tabs,
              children: const [
                _PolicyView(sections: _privacySections),
                _PolicyView(sections: _termsSections),
              ],
            )
          : const _PolicyView(sections: _privacySections),
    );
  }
}

class _PolicyView extends StatelessWidget {
  final List<_Section> sections;
  const _PolicyView({required this.sections});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
      itemCount: sections.length,
      itemBuilder: (context, i) {
        final s = sections[i];
        return Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.heading,
                  style: textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(s.body, style: textTheme.bodyMedium?.copyWith(height: 1.55)),
            ],
          ),
        );
      },
    );
  }
}

class _Section {
  final String heading;
  final String body;
  const _Section(this.heading, this.body);
}

const _privacySections = [
  _Section('Effective Date', 'This Privacy Policy is effective from 1 January 2024.'),
  _Section('Data Controller',
      'VehicleChain is the data controller responsible for personal data collected '
      'through this platform. We are committed to protecting your personal data in '
      'compliance with the Personal Data Protection Act 2010 (PDPA) of Malaysia.'),
  _Section('Personal Data We Collect',
      'We collect and process the following personal data:\n'
      '• Identity data: full name, email address, phone number\n'
      '• Account data: password (stored as a secure hash, never in plain text)\n'
      '• Vehicle data: VIN numbers, ownership records, service history\n'
      '• Technical data: blockchain wallet address, device push notification tokens\n'
      '• Usage data: login timestamps, IP addresses stored in audit logs\n'
      '• Consent records: date and time you accepted this policy'),
  _Section('Purpose of Processing',
      'We process your personal data to:\n'
      '• Provide and manage your vehicle service management account\n'
      '• Record and verify vehicle service history on the blockchain\n'
      '• Process warranty claims and dispute resolutions\n'
      '• Send important notifications about your vehicles and warranties\n'
      '• Detect and prevent fraud or security incidents\n'
      '• Comply with legal obligations under Malaysian law'),
  _Section('Legal Basis for Processing',
      'Under the PDPA 2010, we process your personal data based on:\n'
      '• Your explicit consent given at registration\n'
      '• Performance of the contract between you and VehicleChain\n'
      '• Our legitimate interests in operating a secure and reliable platform\n'
      '• Compliance with applicable legal obligations'),
  _Section('Blockchain and Data Immutability',
      'Vehicle service records submitted to the blockchain are stored permanently '
      'and cannot be deleted. These records contain only hashed identifiers — no '
      'directly identifying personal information (such as your name or email) is '
      'stored on-chain. Your personal details are held only in our secure '
      'off-chain database.'),
  _Section('Data Sharing and Disclosure',
      'We may share your personal data with:\n'
      '• Service centres you authorise to submit records for your vehicle\n'
      '• Manufacturers who registered your vehicle\n'
      '• Third-party service providers operating under data processing agreements\n\n'
      'We do not sell your personal data to any third party.'),
  _Section('Data Retention',
      'We retain your personal data for as long as your account is active. '
      'If you request account deletion, we will delete your personal data within '
      '30 days, except where retention is required by law. Blockchain records '
      'cannot be deleted due to their immutable nature.'),
  _Section('Your Rights Under PDPA',
      'You have the right to:\n'
      '• Access the personal data we hold about you\n'
      '• Correct inaccurate or incomplete personal data\n'
      '• Withdraw consent (note: this may prevent continued use of the service)\n'
      '• Request deletion of your personal data (subject to legal restrictions)\n'
      '• Lodge a complaint with the Personal Data Protection Commissioner of Malaysia\n\n'
      'To exercise these rights, contact: privacy@vehiclechain.my'),
  _Section('Security',
      'We implement appropriate technical and organisational measures to protect your '
      'personal data, including encryption at rest, TLS in transit, bcrypt password '
      'hashing, rate limiting, and blockchain immutability for audit trails.'),
  _Section('Contact Us',
      'For privacy-related queries or to exercise your PDPA rights:\n'
      'Email: privacy@vehiclechain.my\n'
      'Address: VehicleChain Sdn Bhd, Kuala Lumpur, Malaysia'),
];

const _termsSections = [
  _Section('Effective Date', 'These Terms of Service are effective from 1 January 2024.'),
  _Section('Acceptance of Terms',
      'By creating an account and using VehicleChain, you agree to these Terms of Service '
      'and our Privacy Policy. If you do not agree, you must not use this platform.'),
  _Section('Use of the Service',
      'VehicleChain is a vehicle service management platform using blockchain technology '
      'to create tamper-proof service records. You agree to:\n'
      '• Provide accurate and complete registration information\n'
      '• Maintain the confidentiality of your account credentials\n'
      '• Use the platform only for lawful purposes\n'
      '• Not attempt to manipulate, falsify, or tamper with service records'),
  _Section('Blockchain Records',
      'Service records submitted to the blockchain are permanent and immutable. '
      'Once verified or disputed on-chain, a record cannot be erased. You are '
      'responsible for the accuracy of information before approving any service record.'),
  _Section('Account Responsibility',
      'You are responsible for all activity conducted under your account. '
      'Notify us immediately at support@vehiclechain.my if you suspect '
      'unauthorised access to your account.'),
  _Section('Limitation of Liability',
      'VehicleChain is provided "as is". We are not liable for any loss or damage '
      'arising from your use of the platform, including errors in blockchain '
      'transactions, network outages, or unauthorised access resulting from your '
      'failure to protect your credentials.'),
  _Section('Governing Law',
      'These Terms are governed by the laws of Malaysia. Any disputes shall be '
      'subject to the exclusive jurisdiction of the courts of Malaysia.'),
  _Section('Changes to Terms',
      'We may update these Terms from time to time. Continued use of the platform '
      'after changes constitutes your acceptance of the updated Terms.'),
];
