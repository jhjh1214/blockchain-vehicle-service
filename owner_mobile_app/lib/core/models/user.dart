class User {
  final String id;
  final String email;
  final String name;
  final String role;
  final String? phone;
  final String? city;
  final String? state;
  final String blockchainAddress;
  final bool emailVerified;

  const User({
    required this.id,
    required this.email,
    required this.name,
    required this.role,
    this.phone,
    this.city,
    this.state,
    required this.blockchainAddress,
    this.emailVerified = false,
  });

  factory User.fromJson(Map<String, dynamic> j) => User(
        id: j['id'].toString(),
        email: j['email'] ?? '',
        name: j['name'] ?? '',
        role: j['role'] ?? '',
        phone: j['phone'],
        city: j['city'],
        state: j['state'],
        blockchainAddress: j['blockchain_address'] ?? '',
        emailVerified: j['email_verified'] as bool? ?? false,
      );
}
