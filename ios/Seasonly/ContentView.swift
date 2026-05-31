import SwiftUI

struct ContentView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var isPasswordVisible = false
    @State private var hasAttemptedSubmit = false

    private var emailError: String? {
        guard !email.isEmpty else { return "Email is required." }

        let emailPattern = #"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$"#
        let predicate = NSPredicate(format: "SELF MATCHES[c] %@", emailPattern)

        return predicate.evaluate(with: email) ? nil : "Enter a valid email address."
    }

    private var passwordError: String? {
        guard !password.isEmpty else { return "Password is required." }
        return password.count >= 8 ? nil : "Use at least 8 characters."
    }

    private var canSubmit: Bool {
        emailError == nil && passwordError == nil
    }

    var body: some View {
        ZStack {
            RusticBackground()

            VStack(spacing: 28) {
                header

                VStack(spacing: 18) {
                    fieldGroup(
                        title: "Email",
                        error: hasAttemptedSubmit ? emailError : nil
                    ) {
                        TextField("you@example.com", text: $email)
                            .textContentType(.emailAddress)
                            .keyboardType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }

                    fieldGroup(
                        title: "Password",
                        error: hasAttemptedSubmit ? passwordError : nil
                    ) {
                        HStack(spacing: 10) {
                            Group {
                                if isPasswordVisible {
                                    TextField("Password", text: $password)
                                } else {
                                    SecureField("Password", text: $password)
                                }
                            }
                            .textContentType(.password)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()

                            Button {
                                isPasswordVisible.toggle()
                            } label: {
                                Image(systemName: isPasswordVisible ? "eye.slash" : "eye")
                                    .font(.system(size: 18, weight: .semibold))
                                    .foregroundStyle(.secondary)
                                    .frame(width: 36, height: 36)
                                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8))
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel(isPasswordVisible ? "Hide password" : "Show password")
                        }
                    }

                    Button {
                        hasAttemptedSubmit = true
                    } label: {
                        Text("Sign In")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(canSubmit ? Color(red: 0.43, green: 0.25, blue: 0.14) : .gray)
                    .disabled(!canSubmit && hasAttemptedSubmit)

                    Button("Forgot password?") {
                    }
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(Color(red: 0.43, green: 0.25, blue: 0.14))
                }
                .padding(22)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))
                .overlay {
                    RoundedRectangle(cornerRadius: 18)
                        .stroke(.white.opacity(0.48), lineWidth: 1)
                }
                .shadow(color: .black.opacity(0.13), radius: 26, y: 18)
            }
            .padding(.horizontal, 22)
            .frame(maxWidth: 440)
        }
    }

    private var header: some View {
        VStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color(red: 0.51, green: 0.32, blue: 0.18))
                    .frame(width: 58, height: 58)
                    .shadow(color: .black.opacity(0.18), radius: 14, y: 8)

                Image(systemName: "leaf.fill")
                    .font(.system(size: 25, weight: .bold))
                    .foregroundStyle(Color(red: 0.95, green: 0.86, blue: 0.68))
            }

            Text("Welcome Back")
                .font(.largeTitle.weight(.bold))
                .foregroundStyle(Color(red: 0.18, green: 0.12, blue: 0.08))

            Text("Sign in to keep your seasonal plans in rhythm.")
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
    }

    private func fieldGroup<Content: View>(
        title: String,
        error: String?,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color(red: 0.22, green: 0.15, blue: 0.1))

            content()
                .padding(.horizontal, 14)
                .frame(height: 54)
                .background(Color.white.opacity(0.76), in: RoundedRectangle(cornerRadius: 12))
                .overlay {
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(error == nil ? Color.black.opacity(0.08) : .red.opacity(0.55), lineWidth: 1)
                }

            if let error {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .animation(.easeInOut(duration: 0.18), value: error)
    }
}

private struct RusticBackground: View {
    var body: some View {
        LinearGradient(
            colors: [
                Color(red: 0.92, green: 0.84, blue: 0.69),
                Color(red: 0.74, green: 0.82, blue: 0.68),
                Color(red: 0.54, green: 0.64, blue: 0.57)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .ignoresSafeArea()
        .overlay(alignment: .topTrailing) {
            Circle()
                .fill(Color.white.opacity(0.22))
                .frame(width: 220, height: 220)
                .blur(radius: 34)
                .offset(x: 90, y: -70)
        }
        .overlay(alignment: .bottomLeading) {
            Circle()
                .fill(Color(red: 0.38, green: 0.22, blue: 0.13).opacity(0.18))
                .frame(width: 260, height: 260)
                .blur(radius: 42)
                .offset(x: -110, y: 90)
        }
    }
}

#Preview {
    ContentView()
}
