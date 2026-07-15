import SwiftUI

struct ContentView: View {
    @State private var session = AuthenticationSession()

    var body: some View {
        Group {
            if session.isRestoring {
                LaunchView()
            } else if let user = session.user {
                if let profile = session.onboardingProfile {
                    if profile.isCompleted {
                        MainAppView(session: session, user: user) {
                            Task { await session.logout() }
                        }
                    } else {
                        OnboardingView(session: session)
                    }
                } else {
                    LaunchView()
                        .task {
                            await session.loadOnboardingProfile()
                        }
                }
            } else {
                AuthenticationView(session: session)
            }
        }
        .task {
            await session.restore()
        }
    }
}

private struct AuthenticationView: View {
    enum Mode: String, CaseIterable, Identifiable {
        case login = "Sign In"
        case register = "Register"

        var id: Self { self }
    }

    @Bindable var session: AuthenticationSession
    @State private var mode = Mode.login
    @State private var email = ""
    @State private var displayName = ""
    @State private var password = ""
    @State private var confirmation = ""
    @State private var isPasswordVisible = false
    @State private var hasAttemptedSubmit = false
    @State private var showsPasswordReset = false

    private var emailError: String? {
        guard !email.isEmpty else { return "Email is required." }
        let pattern = #"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$"#
        return email.range(of: pattern, options: [.regularExpression, .caseInsensitive]) == nil
            ? "Enter a valid email address."
            : nil
    }

    private var passwordError: String? {
        guard !password.isEmpty else { return "Password is required." }
        return password.count >= 8 ? nil : "Use at least 8 characters."
    }

    private var confirmationError: String? {
        guard mode == .register else { return nil }
        guard !confirmation.isEmpty else { return "Confirm your password." }
        return confirmation == password ? nil : "Passwords do not match."
    }

    private var canSubmit: Bool {
        emailError == nil && passwordError == nil && confirmationError == nil
    }

    var body: some View {
        ZStack {
            RusticBackground()

            ScrollView {
                VStack(spacing: 24) {
                    AuthHeader(mode: mode)

                    VStack(spacing: 18) {
                        Picker("Authentication mode", selection: $mode) {
                            ForEach(Mode.allCases) { mode in
                                Text(mode.rawValue).tag(mode)
                            }
                        }
                        .pickerStyle(.segmented)
                        .onChange(of: mode) {
                            hasAttemptedSubmit = false
                            session.errorMessage = nil
                        }

                        if mode == .register {
                            AuthField(title: "Display name", error: nil) {
                                TextField("Your name (optional)", text: $displayName)
                                    .textContentType(.name)
                                    .textInputAutocapitalization(.words)
                            }
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }

                        AuthField(title: "Email", error: hasAttemptedSubmit ? emailError : nil) {
                            TextField("you@example.com", text: $email)
                                .textContentType(.emailAddress)
                                .keyboardType(.emailAddress)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                        }

                        AuthField(title: "Password", error: hasAttemptedSubmit ? passwordError : nil) {
                            PasswordEntry(
                                placeholder: "Password",
                                password: $password,
                                isVisible: $isPasswordVisible,
                                contentType: mode == .login ? .password : .newPassword
                            )
                        }

                        if mode == .register {
                            AuthField(
                                title: "Confirm password",
                                error: hasAttemptedSubmit ? confirmationError : nil
                            ) {
                                SecureField("Confirm password", text: $confirmation)
                                    .textContentType(.newPassword)
                            }
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }

                        if let errorMessage = session.errorMessage {
                            StatusMessage(message: errorMessage, isError: true)
                        }

                        Button {
                            submit()
                        } label: {
                            Group {
                                if session.isLoading {
                                    ProgressView()
                                        .tint(.white)
                                } else {
                                    Text(mode == .login ? "Sign In" : "Create Account")
                                }
                            }
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(canSubmit ? SeasonlyColors.brown : .gray)
                        .disabled(session.isLoading || (!canSubmit && hasAttemptedSubmit))

                        if mode == .login {
                            Button("Forgot password?") {
                                showsPasswordReset = true
                            }
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(SeasonlyColors.brown)
                        }
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
                .padding(.vertical, 30)
                .frame(maxWidth: 440)
                .frame(maxWidth: .infinity)
            }
            .scrollDismissesKeyboard(.interactively)
        }
        .animation(.easeInOut(duration: 0.2), value: mode)
        .sheet(isPresented: $showsPasswordReset) {
            PasswordResetView(session: session, initialEmail: email)
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }

    private func submit() {
        hasAttemptedSubmit = true
        session.errorMessage = nil
        guard canSubmit else { return }

        Task {
            switch mode {
            case .login:
                _ = await session.login(email: email, password: password)
            case .register:
                _ = await session.register(
                    email: email,
                    password: password,
                    displayName: displayName.trimmingCharacters(in: .whitespacesAndNewlines)
                )
            }
        }
    }
}

private struct PasswordResetView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var session: AuthenticationSession
    @State private var email: String
    @State private var hasAttemptedSubmit = false
    @State private var confirmationMessage: String?
    @State private var resetToken = ""
    @State private var newPassword = ""
    @State private var passwordConfirmation = ""
    @State private var resetComplete = false

    init(session: AuthenticationSession, initialEmail: String) {
        self.session = session
        _email = State(initialValue: initialEmail)
    }

    private var emailError: String? {
        guard !email.isEmpty else { return "Email is required." }
        let pattern = #"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$"#
        return email.range(of: pattern, options: [.regularExpression, .caseInsensitive]) == nil
            ? "Enter a valid email address."
            : nil
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 18) {
                Text("Reset your password")
                    .font(.title2.weight(.bold))
                    .foregroundStyle(SeasonlyColors.ink)

                Text("Enter your account email and we’ll request reset instructions from Seasonly.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                if confirmationMessage == nil {
                    AuthField(title: "Email", error: hasAttemptedSubmit ? emailError : nil) {
                        TextField("you@example.com", text: $email)
                            .textContentType(.emailAddress)
                            .keyboardType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }
                } else if !resetComplete {
                    Text("Check your email, then enter the one-time token and a new password.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    AuthField(title: "Reset token", error: nil) {
                        TextField("One-time token", text: $resetToken)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }

                    AuthField(title: "New password", error: nil) {
                        SecureField("At least 8 characters", text: $newPassword)
                            .textContentType(.newPassword)
                    }

                    AuthField(title: "Confirm password", error: nil) {
                        SecureField("Confirm new password", text: $passwordConfirmation)
                            .textContentType(.newPassword)
                    }
                }

                if resetComplete, let confirmationMessage {
                    StatusMessage(message: confirmationMessage, isError: false)
                } else if let errorMessage = session.errorMessage {
                    StatusMessage(message: errorMessage, isError: true)
                }

                Button {
                    if confirmationMessage == nil {
                        requestReset()
                    } else {
                        confirmReset()
                    }
                } label: {
                    Group {
                        if session.isLoading {
                            ProgressView().tint(.white)
                        } else {
                            Text(confirmationMessage == nil ? "Request Reset" : "Reset Password")
                        }
                    }
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
                }
                .buttonStyle(.borderedProminent)
                .tint(SeasonlyColors.brown)
                .disabled(
                    session.isLoading
                        || resetComplete
                        || (confirmationMessage != nil
                            && (resetToken.isEmpty
                                || newPassword.count < 8
                                || newPassword != passwordConfirmation))
                )

                Spacer()
            }
            .padding(22)
            .background(Color(red: 0.94, green: 0.91, blue: 0.83))
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .onAppear { session.errorMessage = nil }
    }

    private func requestReset() {
        hasAttemptedSubmit = true
        session.errorMessage = nil
        guard emailError == nil else { return }

        Task {
            confirmationMessage = await session.requestPasswordReset(email: email)
        }
    }

    private func confirmReset() {
        session.errorMessage = nil
        guard !resetToken.isEmpty,
              newPassword.count >= 8,
              newPassword == passwordConfirmation else { return }

        Task {
            if let message = await session.confirmPasswordReset(
                resetToken: resetToken,
                newPassword: newPassword
            ) {
                confirmationMessage = message
                resetComplete = true
            }
        }
    }
}

private struct LaunchView: View {
    var body: some View {
        ZStack {
            RusticBackground()
            VStack(spacing: 16) {
                SeasonlyMark()
                ProgressView()
                    .tint(SeasonlyColors.brown)
            }
        }
    }
}

private struct AuthHeader: View {
    let mode: AuthenticationView.Mode

    var body: some View {
        VStack(spacing: 10) {
            SeasonlyMark()

            Text(mode == .login ? "Welcome Back" : "Join Seasonly")
                .font(.largeTitle.weight(.bold))
                .foregroundStyle(SeasonlyColors.ink)

            Text(mode == .login
                 ? "Sign in to keep your seasonal plans in rhythm."
                 : "Create an account and start planning with the seasons.")
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
    }
}

private struct SeasonlyMark: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(red: 0.51, green: 0.32, blue: 0.18))
                .frame(width: 58, height: 58)
                .shadow(color: .black.opacity(0.18), radius: 14, y: 8)

            Image(systemName: "leaf.fill")
                .font(.system(size: 25, weight: .bold))
                .foregroundStyle(Color(red: 0.95, green: 0.86, blue: 0.68))
        }
    }
}

private struct PasswordEntry: View {
    let placeholder: String
    @Binding var password: String
    @Binding var isVisible: Bool
    let contentType: UITextContentType

    var body: some View {
        HStack(spacing: 10) {
            Group {
                if isVisible {
                    TextField(placeholder, text: $password)
                } else {
                    SecureField(placeholder, text: $password)
                }
            }
            .textContentType(contentType)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()

            Button {
                isVisible.toggle()
            } label: {
                Image(systemName: isVisible ? "eye.slash" : "eye")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 36, height: 36)
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isVisible ? "Hide password" : "Show password")
        }
    }
}

private struct AuthField<Content: View>: View {
    let title: String
    let error: String?
    @ViewBuilder let content: Content

    init(title: String, error: String?, @ViewBuilder content: () -> Content) {
        self.title = title
        self.error = error
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(SeasonlyColors.ink)

            content
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

struct StatusMessage: View {
    let message: String
    let isError: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: isError ? "exclamationmark.circle.fill" : "checkmark.circle.fill")
            Text(message)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .font(.caption)
        .foregroundStyle(isError ? .red : Color(red: 0.16, green: 0.42, blue: 0.22))
    }
}

struct RusticBackground: View {
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
                .fill(SeasonlyColors.brown.opacity(0.18))
                .frame(width: 260, height: 260)
                .blur(radius: 42)
                .offset(x: -110, y: 90)
        }
    }
}

enum SeasonlyColors {
    static let brown = Color(red: 0.43, green: 0.25, blue: 0.14)
    static let ink = Color(red: 0.22, green: 0.15, blue: 0.1)
}

#Preview {
    ContentView()
}
