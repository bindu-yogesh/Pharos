import 'package:flutter/material.dart';
import 'home_screen.dart';
import 'route_planner_screen.dart';
import 'live_map_screen.dart';
import 'safe_places_screen.dart';
import 'report_hazard_screen.dart';

// Global state to track login status across widgets
bool isUserLoggedIn = false;

class MainNavigation extends StatefulWidget {
  const MainNavigation({super.key});

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const HomeScreen(),
    const RoutePlannerScreen(),
    const LiveMapScreen(),
    const SafePlacesScreen(),
    const ReportHazardScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        backgroundColor: const Color(0xFF1E293B),
        selectedItemColor: Colors.cyanAccent,
        unselectedItemColor: Colors.grey,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_outlined), activeIcon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.alt_route), activeIcon: Icon(Icons.alt_route), label: 'Route'),
          BottomNavigationBarItem(icon: Icon(Icons.map_outlined), activeIcon: Icon(Icons.map), label: 'Map'),
          BottomNavigationBarItem(icon: Icon(Icons.local_hospital_outlined), activeIcon: Icon(Icons.local_hospital), label: 'Safe'),
          BottomNavigationBarItem(icon: Icon(Icons.warning_amber_rounded), activeIcon: Icon(Icons.warning), label: 'Report'),
        ],
      ),
    );
  }
}

class PharosAppBar extends StatefulWidget implements PreferredSizeWidget {
  const PharosAppBar({super.key});

  @override
  Size get preferredSize => const Size.fromHeight(60);

  @override
  State<PharosAppBar> createState() => _PharosAppBarState();
}

class _PharosAppBarState extends State<PharosAppBar> {
  void _showLoginDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF162032),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.lock_outline, color: Colors.cyanAccent),
              SizedBox(width: 10),
              Text("User Login", style: TextStyle(color: Colors.white)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("Please sign in to access emergency broadcast alerts and personalized route history.", style: TextStyle(color: Colors.grey, fontSize: 13)),
              const SizedBox(height: 16),
              TextField(
                decoration: InputDecoration(
                  hintText: "Enter Email or Phone",
                  hintStyle: const TextStyle(color: Colors.grey),
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                obscureText: true,
                decoration: InputDecoration(
                  hintText: "Password",
                  hintStyle: const TextStyle(color: Colors.grey),
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text("Cancel", style: TextStyle(color: Colors.grey)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0055FF)),
              onPressed: () {
                setState(() {
                  isUserLoggedIn = true;
                });
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Successfully Logged In to Pharos Profile!")),
                );
              },
              child: const Text("Login", style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );
  }

  void _showNotificationsModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF162032),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text("Notifications", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.grey),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const Divider(color: Colors.white12),
              const SizedBox(height: 12),
              isUserLoggedIn
                  ? Column(
                      children: const [
                        ListTile(
                          leading: Icon(Icons.warning_amber, color: Colors.orangeAccent),
                          title: Text("Hairpin Curve Advisory", style: TextStyle(color: Colors.white, fontSize: 14)),
                          subtitle: Text("Light rain reported near Shiradi Ghat km 240.", style: TextStyle(color: Colors.grey, fontSize: 11)),
                        ),
                        Divider(color: Colors.white12),
                        ListTile(
                          leading: Icon(Icons.check_circle, color: Colors.greenAccent),
                          title: Text("Corridor Clear", style: TextStyle(color: Colors.white, fontSize: 14)),
                          subtitle: Text("NH 75 traffic flow is currently smooth.", style: TextStyle(color: Colors.grey, fontSize: 11)),
                        ),
                      ],
                    )
                  : Column(
                      children: [
                        const Icon(Icons.notifications_off_outlined, size: 48, color: Colors.grey),
                        const SizedBox(height: 12),
                        const Text("No notifications yet.", style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 6),
                        const Text("Login to get real-time safety alerts and emergency updates.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey, fontSize: 13)),
                        const SizedBox(height: 20),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0055FF)),
                          onPressed: () {
                            Navigator.pop(context);
                            _showLoginDialog(context);
                          },
                          child: const Text("Login Now", style: TextStyle(color: Colors.white)),
                        ),
                      ],
                    ),
              const SizedBox(height: 20),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: Colors.cyan.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.shield, color: Colors.cyanAccent, size: 20),
          ),
          const SizedBox(width: 10),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Pharos",
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
              ),
              Text(
                "Safer Roads, Brighter Tomorrows.",
                style: TextStyle(color: Colors.grey, fontSize: 10),
              ),
            ],
          ),
        ],
      ),
      actions: [
        IconButton(
          icon: const Icon(Icons.notifications_outlined, color: Colors.white70),
          onPressed: () => _showNotificationsModal(context),
        ),
        Padding(
          padding: const EdgeInsets.only(right: 12.0),
          child: GestureDetector(
            onTap: () => _showLoginDialog(context),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: isUserLoggedIn ? Colors.green.withOpacity(0.3) : Colors.cyan.withOpacity(0.3),
              child: Icon(isUserLoggedIn ? Icons.person : Icons.person_outline, color: isUserLoggedIn ? Colors.greenAccent : Colors.cyanAccent, size: 20),
            ),
          ),
        ),
      ],
    );
  }
}