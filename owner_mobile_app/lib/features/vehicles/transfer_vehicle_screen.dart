import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'vehicles_provider.dart';

class TransferVehicleScreen extends StatefulWidget {
  final String vin;
  const TransferVehicleScreen({super.key, required this.vin});

  @override
  State<TransferVehicleScreen> createState() => _TransferVehicleScreenState();
}

class _TransferVehicleScreenState extends State<TransferVehicleScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  bool _loading = false;
  bool _confirmed = false;

  @override
  void dispose() {
    _emailCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_confirmed) {
      setState(() => _confirmed = true);
      return;
    }
    setState(() => _loading = true);
    final error = await context
        .read<VehiclesProvider>()
        .transferVehicle(widget.vin, _emailCtrl.text.trim().toLowerCase());
    if (!mounted) return;
    setState(() => _loading = false);
    if (error == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Vehicle transferred successfully'),
            backgroundColor: Colors.green),
      );
      context.go('/home');
    } else {
      setState(() => _confirmed = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Transfer Ownership')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.1),
                  border: Border.all(color: Colors.orange),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber, color: Colors.orange),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Transferring ownership is permanent and recorded on the blockchain. This action cannot be undone.',
                        style: TextStyle(color: Colors.orange[800], fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Text('VIN: ${widget.vin}',
                  style: const TextStyle(
                      fontFamily: 'monospace',
                      fontWeight: FontWeight.w500)),
              const SizedBox(height: 24),
              TextFormField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'New Owner Email',
                  prefixIcon: Icon(Icons.person_outlined),
                  hintText: 'Enter the new owner\'s registered email',
                ),
                validator: (v) =>
                    v == null || !v.contains('@') ? 'Enter a valid email' : null,
              ),
              const SizedBox(height: 24),
              if (_confirmed)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.withOpacity(0.1),
                    border: Border.all(color: Colors.red),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Confirm: Transfer VIN ${widget.vin} to ${_emailCtrl.text}?',
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  ),
                ),
              ElevatedButton(
                onPressed: _loading ? null : _submit,
                style: ElevatedButton.styleFrom(
                    backgroundColor:
                        _confirmed ? Colors.red : null),
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : Text(_confirmed ? 'Confirm Transfer' : 'Transfer Vehicle'),
              ),
              if (_confirmed) ...[
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () => setState(() => _confirmed = false),
                  child: const Text('Cancel'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
