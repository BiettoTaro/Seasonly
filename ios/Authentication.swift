import Foundation
import Observation
import Security

struct UserProfile: Codable, Sendable {
    let userId: UUID
    let displayName: String?
    let countryCode: String?
    let regionCode: String?
    let locationSource: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case displayName = "display_name"
        case countryCode = "country_code"
        case regionCode = "region_code"
        case locationSource = "location_source"
    }
}

struct SeasonlyUser: Codable, Sendable {
    let id: UUID
    let email: String
    let isActive: Bool
    let isVerified: Bool
    let createdAt: Date
    let updatedAt: Date
    let profile: UserProfile?

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case isActive = "is_active"
        case isVerified = "is_verified"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case profile
    }
}

struct TokenResponse: Codable, Sendable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
    }
}

private struct RegistrationRequest: Encodable {
    let email: String
    let password: String
    let profile: RegistrationProfile?
}

private struct RegistrationProfile: Encodable {
    let displayName: String

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
    }
}

private struct RefreshTokenRequest: Codable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

private struct PasswordResetRequest: Encodable {
    let email: String
}

private struct MessageResponse: Decodable {
    let message: String
}

private struct APIErrorResponse: Decodable {
    let detail: APIErrorDetail
}

private enum APIErrorDetail: Decodable {
    case message(String)
    case validation([ValidationIssue])

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let message = try? container.decode(String.self) {
            self = .message(message)
        } else {
            self = .validation(try container.decode([ValidationIssue].self))
        }
    }

    var message: String {
        switch self {
        case .message(let message):
            return message
        case .validation(let issues):
            return issues.first?.message ?? "The request could not be completed."
        }
    }
}

private struct ValidationIssue: Decodable {
    let message: String

    enum CodingKeys: String, CodingKey {
        case message = "msg"
    }
}

enum AuthenticationError: LocalizedError {
    case invalidResponse
    case server(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an unexpected response."
        case .server(let message):
            return message
        }
    }
}

struct AuthenticationClient: Sendable {
    private let baseURL: URL
    private let session: URLSession
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(baseURL: URL = AuthenticationClient.defaultBaseURL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
    }

    static var defaultBaseURL: URL {
        if let override = ProcessInfo.processInfo.environment["SEASONLY_API_BASE_URL"],
           let url = URL(string: override) {
            return url
        }
        return URL(string: "http://127.0.0.1:8000/api/v1")!
    }

    func login(email: String, password: String) async throws -> TokenResponse {
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "username", value: email),
            URLQueryItem(name: "password", value: password)
        ]

        var request = request(path: "auth/token", method: "POST")
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = components.percentEncodedQuery?.data(using: .utf8)
        return try await send(request)
    }

    func register(email: String, password: String, displayName: String) async throws -> SeasonlyUser {
        let profile = displayName.isEmpty ? nil : RegistrationProfile(displayName: displayName)
        let payload = RegistrationRequest(email: email, password: password, profile: profile)
        return try await sendJSON(path: "users", method: "POST", payload: payload)
    }

    func currentUser(accessToken: String) async throws -> SeasonlyUser {
        var request = request(path: "users/me", method: "GET")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        return try await send(request)
    }

    func refresh(refreshToken: String) async throws -> TokenResponse {
        try await sendJSON(
            path: "auth/refresh",
            method: "POST",
            payload: RefreshTokenRequest(refreshToken: refreshToken)
        )
    }

    func logout(refreshToken: String) async throws {
        let _: EmptyResponse = try await sendJSON(
            path: "auth/logout",
            method: "POST",
            payload: RefreshTokenRequest(refreshToken: refreshToken)
        )
    }

    func requestPasswordReset(email: String) async throws -> String {
        let response: MessageResponse = try await sendJSON(
            path: "auth/password-reset/request",
            method: "POST",
            payload: PasswordResetRequest(email: email)
        )
        return response.message
    }

    private func sendJSON<Response: Decodable, Payload: Encodable>(
        path: String,
        method: String,
        payload: Payload
    ) async throws -> Response {
        var request = request(path: path, method: method)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(payload)
        return try await send(request)
    }

    private func request(path: String, method: String) -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return request
    }

    private func send<Response: Decodable>(_ request: URLRequest) async throws -> Response {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthenticationError.invalidResponse
        }

        guard 200..<300 ~= httpResponse.statusCode else {
            let apiError = try? decoder.decode(APIErrorResponse.self, from: data)
            throw AuthenticationError.server(apiError?.detail.message ?? "Request failed (\(httpResponse.statusCode)).")
        }

        if Response.self == EmptyResponse.self, data.isEmpty {
            return EmptyResponse() as! Response
        }
        return try decoder.decode(Response.self, from: data)
    }
}

private struct EmptyResponse: Decodable {
}

private struct TokenStore {
    private let service = "com.seasonly.authentication"
    private let account = "session-tokens"

    func save(_ tokens: TokenResponse) throws {
        let data = try JSONEncoder().encode(tokens)
        let query = baseQuery
        SecItemDelete(query as CFDictionary)

        var attributes = query
        attributes[kSecValueData as String] = data
        let status = SecItemAdd(attributes as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw AuthenticationError.server("The session could not be saved securely.")
        }
    }

    func load() -> TokenResponse? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else {
            return nil
        }
        return try? JSONDecoder().decode(TokenResponse.self, from: data)
    }

    func clear() {
        SecItemDelete(baseQuery as CFDictionary)
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }
}

@MainActor
@Observable
final class AuthenticationSession {
    private(set) var user: SeasonlyUser?
    private(set) var isRestoring = true
    private(set) var isLoading = false
    var errorMessage: String?

    private let client: AuthenticationClient
    private let tokenStore = TokenStore()
    private var tokens: TokenResponse?

    init(client: AuthenticationClient? = nil) {
        self.client = client ?? AuthenticationClient()
    }

    func restore() async {
        defer { isRestoring = false }
        guard let storedTokens = tokenStore.load() else { return }

        do {
            user = try await client.currentUser(accessToken: storedTokens.accessToken)
            tokens = storedTokens
        } catch {
            do {
                let refreshedTokens = try await client.refresh(refreshToken: storedTokens.refreshToken)
                try tokenStore.save(refreshedTokens)
                tokens = refreshedTokens
                user = try await client.currentUser(accessToken: refreshedTokens.accessToken)
            } catch {
                tokenStore.clear()
            }
        }
    }

    func login(email: String, password: String) async -> Bool {
        await performAuthentication {
            try await client.login(email: email, password: password)
        }
    }

    func register(email: String, password: String, displayName: String) async -> Bool {
        await performAuthentication {
            _ = try await client.register(email: email, password: password, displayName: displayName)
            return try await client.login(email: email, password: password)
        }
    }

    func requestPasswordReset(email: String) async -> String? {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            return try await client.requestPasswordReset(email: email)
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func logout() async {
        let refreshToken = tokens?.refreshToken
        user = nil
        tokens = nil
        tokenStore.clear()

        if let refreshToken {
            try? await client.logout(refreshToken: refreshToken)
        }
    }

    private func performAuthentication(
        getTokens: () async throws -> TokenResponse
    ) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let newTokens = try await getTokens()
            let authenticatedUser = try await client.currentUser(accessToken: newTokens.accessToken)
            try tokenStore.save(newTokens)
            tokens = newTokens
            user = authenticatedUser
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }
}
