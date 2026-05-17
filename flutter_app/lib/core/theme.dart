import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// App theme — Material 3, dark mode with premium feel.
class AppTheme {
  AppTheme._();

  // Brand colors
  static const Color primary = Color(0xFF6366F1);      // Indigo
  static const Color secondary = Color(0xFF8B5CF6);     // Purple
  static const Color accent = Color(0xFF06B6D4);        // Cyan
  static const Color surface = Color(0xFF1E1E2E);       // Dark surface
  static const Color background = Color(0xFF0F0F1A);    // Deep dark
  static const Color card = Color(0xFF262640);           // Card background
  static const Color cardBorder = Color(0xFF3B3B5C);    // Card border
  static const Color textPrimary = Color(0xFFF1F1F5);   // White text
  static const Color textSecondary = Color(0xFF9CA3AF);  // Gray text
  static const Color safe = Color(0xFF22C55E);           // Green
  static const Color caution = Color(0xFFF59E0B);        // Amber
  static const Color risky = Color(0xFFEF4444);          // Red
  static const Color income = Color(0xFF22C55E);         // Green
  static const Color expense = Color(0xFFEF4444);        // Red

  static ThemeData get darkTheme {
    final textTheme = GoogleFonts.interTextTheme(ThemeData.dark().textTheme);
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.dark(
        primary: primary,
        secondary: secondary,
        tertiary: accent,
        surface: surface,
        onSurface: textPrimary,
      ),
      scaffoldBackgroundColor: background,
      textTheme: textTheme.copyWith(
        headlineLarge: textTheme.headlineLarge?.copyWith(
          color: textPrimary, fontWeight: FontWeight.bold,
        ),
        titleLarge: textTheme.titleLarge?.copyWith(
          color: textPrimary, fontWeight: FontWeight.w600,
        ),
        bodyMedium: textTheme.bodyMedium?.copyWith(color: textSecondary),
        bodySmall: textTheme.bodySmall?.copyWith(color: textSecondary),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: cardBorder, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: card,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: primary,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}
