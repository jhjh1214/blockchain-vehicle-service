import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

interface PolicySection {
  heading: string;
  body: string;
}

const PRIVACY_SECTIONS: PolicySection[] = [
  { heading: 'Effective Date', body: 'This Privacy Policy is effective from 1 January 2024.' },
  { heading: 'Data Controller',
    body: 'VehicleChain is the data controller responsible for personal data collected through this platform. We are committed to protecting your personal data in compliance with the Personal Data Protection Act 2010 (PDPA) of Malaysia.' },
  { heading: 'Personal Data We Collect',
    body: 'We collect and process the following personal data:\n• Identity data: full name, email address, phone number\n• Account data: password (stored as a secure hash, never in plain text)\n• Vehicle data: VIN numbers, ownership records, service history\n• Technical data: blockchain wallet address, device push notification tokens\n• Usage data: login timestamps, IP addresses stored in audit logs\n• Consent records: date and time you accepted this policy' },
  { heading: 'Purpose of Processing',
    body: 'We process your personal data to:\n• Provide and manage your vehicle service management account\n• Record and verify vehicle service history on the blockchain\n• Process warranty claims and dispute resolutions\n• Send important notifications about your vehicles and warranties\n• Detect and prevent fraud or security incidents\n• Comply with legal obligations under Malaysian law' },
  { heading: 'Legal Basis for Processing',
    body: 'Under the PDPA 2010, we process your personal data based on:\n• Your explicit consent given at registration\n• Performance of the contract between you and VehicleChain\n• Our legitimate interests in operating a secure and reliable platform\n• Compliance with applicable legal obligations' },
  { heading: 'Blockchain and Data Immutability',
    body: 'Vehicle service records submitted to the blockchain are stored permanently and cannot be deleted. These records contain only hashed identifiers — no directly identifying personal information (such as your name or email) is stored on-chain. Your personal details are held only in our secure off-chain database.' },
  { heading: 'Data Sharing and Disclosure',
    body: 'We may share your personal data with:\n• Service centres you authorise to submit records for your vehicle\n• Manufacturers who registered your vehicle\n• Third-party service providers operating under data processing agreements\n\nWe do not sell your personal data to any third party.' },
  { heading: 'Data Retention',
    body: 'We retain your personal data for as long as your account is active. If you request account deletion, we will delete your personal data within 30 days, except where retention is required by law. Blockchain records cannot be deleted due to their immutable nature.' },
  { heading: 'Your Rights Under PDPA',
    body: 'You have the right to:\n• Access the personal data we hold about you\n• Correct inaccurate or incomplete personal data\n• Withdraw consent (note: this may prevent continued use of the service)\n• Request deletion of your personal data (subject to legal restrictions)\n• Lodge a complaint with the Personal Data Protection Commissioner of Malaysia\n\nTo exercise these rights, contact: privacy@vehiclechain.my' },
  { heading: 'Security',
    body: 'We implement appropriate technical and organisational measures to protect your personal data, including encryption at rest, TLS in transit, bcrypt password hashing, rate limiting, and blockchain immutability for audit trails.' },
  { heading: 'Contact Us',
    body: 'For privacy-related queries or to exercise your PDPA rights:\nEmail: privacy@vehiclechain.my\nAddress: VehicleChain Sdn Bhd, Kuala Lumpur, Malaysia' },
];

const TERMS_SECTIONS: PolicySection[] = [
  { heading: 'Effective Date', body: 'These Terms of Service are effective from 1 January 2024.' },
  { heading: 'Acceptance of Terms',
    body: 'By creating an account and using VehicleChain, you agree to these Terms of Service and our Privacy Policy. If you do not agree, you must not use this platform.' },
  { heading: 'Use of the Service',
    body: 'VehicleChain is a vehicle service management platform using blockchain technology to create tamper-proof service records. You agree to:\n• Provide accurate and complete registration information\n• Maintain the confidentiality of your account credentials\n• Use the platform only for lawful purposes\n• Not attempt to manipulate, falsify, or tamper with service records' },
  { heading: 'Blockchain Records',
    body: 'Service records submitted to the blockchain are permanent and immutable. Once verified or disputed on-chain, a record cannot be erased. You are responsible for the accuracy of information before approving any service record.' },
  { heading: 'Account Responsibility',
    body: 'You are responsible for all activity conducted under your account. Notify us immediately at support@vehiclechain.my if you suspect unauthorised access to your account.' },
  { heading: 'Limitation of Liability',
    body: 'VehicleChain is provided "as is". We are not liable for any loss or damage arising from your use of the platform, including errors in blockchain transactions, network outages, or unauthorised access resulting from your failure to protect your credentials.' },
  { heading: 'Governing Law',
    body: 'These Terms are governed by the laws of Malaysia. Any disputes shall be subject to the exclusive jurisdiction of the courts of Malaysia.' },
  { heading: 'Changes to Terms',
    body: 'We may update these Terms from time to time. Continued use of the platform after changes constitutes your acceptance of the updated Terms.' },
];

@Component({
  selector: 'app-privacy-policy',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './privacy-policy.html',
  styleUrls: ['./privacy-policy.css']
})
export class PrivacyPolicyComponent {
  activeTab: 'privacy' | 'terms' = 'privacy';
  privacySections = PRIVACY_SECTIONS;
  termsSections = TERMS_SECTIONS;

  get sections(): PolicySection[] {
    return this.activeTab === 'privacy' ? this.privacySections : this.termsSections;
  }
}
