import SwiftUI

enum SeasonlyLegal {
    static let termsVersion = "2026-08-27"
    static let privacyNoticeVersion = "2026-08-27"
}

struct LegalSection: Identifiable, Sendable {
    let title: String
    let body: String

    var id: String { title }
}

enum LegalDocument: String, Identifiable, Sendable {
    case termsOfUse
    case privacyNotice

    var id: String { rawValue }

    var title: String {
        switch self {
        case .termsOfUse: "Terms of Use"
        case .privacyNotice: "Privacy Notice"
        }
    }

    var version: String {
        switch self {
        case .termsOfUse: SeasonlyLegal.termsVersion
        case .privacyNotice: SeasonlyLegal.privacyNoticeVersion
        }
    }

    var effectiveDate: String { "27 August 2026" }

    var introduction: String {
        switch self {
        case .termsOfUse:
            "Seasonly is a free, non-production academic minimum viable product. By creating an account and selecting ‘I agree to the Terms of Use’, you agree to these Terms."
        case .privacyNotice:
            "This notice explains how the Seasonly academic MVP collects and uses personal information. It is provided when you create an account and remains available during onboarding."
        }
    }

    var sections: [LegalSection] {
        switch self {
        case .termsOfUse: Self.termsSections
        case .privacyNotice: Self.privacySections
        }
    }

    private static let termsSections = [
        LegalSection(
            title: "1. About Seasonly",
            body: "Seasonly is a final-year software engineering project that helps users discover seasonal recipes, record food preferences, save favourites, plan meals and receive recipe suggestions. It is intended for private testing and academic evaluation. It is not a commercial food, medical or nutrition service."
        ),
        LegalSection(
            title: "2. Who may use Seasonly",
            body: "You must be at least 18 years old and capable of agreeing to these Terms. The academic MVP is provided only to invited testers and authorised project participants. You must not give another person access to your account."
        ),
        LegalSection(
            title: "3. Your account",
            body: "You must provide a valid email address and keep your password confidential. You are responsible for activity performed through your account unless it results from a failure by Seasonly to use reasonable care. Notify the project developer if you believe your account has been accessed without permission. You may permanently delete your account through the profile controls."
        ),
        LegalSection(
            title: "4. What Seasonly provides",
            body: "Seasonly may provide country-level seasonal produce information, recipe discovery, dietary and ingredient filtering, allergy-aware filtering where adequate source evidence exists, favourites, recipe history, weekly planning and preference-based recommendations where personalisation is enabled. The MVP is free and has no subscriptions or in-app purchases. Features, recipe coverage and supported countries may change during evaluation."
        ),
        LegalSection(
            title: "5. Food, allergy and health information",
            body: "Seasonly provides general information, not medical, nutritional or dietary advice. Recipe data may come from third parties and may be incomplete, outdated or inaccurate. It may omit compound ingredients, substitutions, preparation practices or cross-contamination risks. Conservative filtering does not guarantee that a recipe is allergen-free or safe.\n\nYou must independently check complete ingredient lists, product packaging, manufacturer warnings, substitutions, preparation methods and cross-contamination risks. People with allergies, medical conditions or specialist dietary requirements should seek advice from an appropriately qualified professional. Seasonly must not be used in an emergency and does not provide verified medical, religious or cultural certification."
        ),
        LegalSection(
            title: "6. Seasonality and recommendations",
            body: "Seasonal information is based on supported country-level datasets and calendar months. It does not guarantee local availability, retailer stock, product origin, environmental performance or growing conditions. Recommendations are automated suggestions based on seasonal matches, declared preferences and, where separately enabled, previous interactions. You remain responsible for deciding whether to prepare, purchase or consume any ingredient or recipe."
        ),
        LegalSection(
            title: "7. Personal data and optional consent",
            body: "The Privacy Notice explains what personal data is collected, why it is used, how long it is retained and what rights are available. Agreement to these Terms does not provide consent for optional personalisation or allergy-data processing. Seasonly requests those consents separately and allows them to be withdrawn."
        ),
        LegalSection(
            title: "8. Acceptable use",
            body: "You must not access another user’s account, interfere with the service or its security, submit malicious or automated requests, unlawfully extract or redistribute datasets, use the MVP for an unlawful purpose, or represent its recommendations as professionally verified medical or allergy advice. Access may be suspended where reasonably necessary to protect users, data, the service or the academic evaluation."
        ),
        LegalSection(
            title: "9. Third-party material",
            body: "Seasonly may display recipes, images, instructions and seasonal information obtained from third-party sources. Ownership remains with the relevant provider or rights holder. Third-party sources may have their own terms, licences and privacy practices. Seasonly does not guarantee that an external source will remain available."
        ),
        LegalSection(
            title: "10. Availability and changes",
            body: "Because Seasonly is an academic prototype, it may be unavailable, contain errors or be withdrawn after evaluation. Reasonable notice will be provided where practical if the MVP is discontinued or a material change affects existing users. Material changes to these Terms will be presented before the revised Terms become binding. If you disagree, you may stop using Seasonly and delete your account."
        ),
        LegalSection(
            title: "11. Responsibility and legal rights",
            body: "Seasonly will use reasonable care in providing the MVP. Nothing in these Terms excludes responsibility where doing so would be unlawful, including responsibility for death or personal injury caused by negligence, fraud, or rights that cannot be excluded under consumer law. Seasonly is not responsible for loss caused by inaccurate third-party information where reasonable care has been used, or for loss that could not reasonably have been anticipated when these Terms were accepted. Nothing in these Terms affects your statutory rights."
        ),
        LegalSection(
            title: "12. Ending use",
            body: "You may stop using Seasonly at any time and delete your account through the app. Seasonly may suspend or end access if you materially breach these Terms, create a security risk, misuse third-party data, or if the academic MVP is discontinued. Where appropriate, you will be given an explanation and a reasonable opportunity to export or delete your information."
        ),
        LegalSection(
            title: "13. Governing law",
            body: "These Terms are governed by the laws of England and Wales. Mandatory consumer rights in the country where you live remain unaffected. Disputes should first be raised with the project developer so an informal resolution can be attempted. Nothing prevents either party from using a court or another remedy available under applicable law."
        ),
        LegalSection(
            title: "14. Contact",
            body: "Questions about Seasonly, these Terms or account access should be sent to the project developer using the contact details supplied with the private testing invitation."
        ),
    ]

    private static let privacySections = [
        LegalSection(
            title: "1. Who is responsible",
            body: "The Seasonly project developer is responsible for personal information processed by this private academic MVP. Contact the developer using the details supplied with the private testing invitation. Seasonly is not offered as a public or commercial service."
        ),
        LegalSection(
            title: "2. Information Seasonly collects",
            body: "Seasonly stores your email address, a securely hashed password, account timestamps and an optional display name. During onboarding it may store your selected country, an optional coarse region, how that location was selected, diet type, allergy status and disclosed allergens, foods avoided, cuisine preferences and protein preferences.\n\nThe app may also store favourites, recipe-view history, planned meals, consent records, recommendation interactions, session metadata and password-reset metadata. Precise coordinates, IP addresses, device identifiers and free-text allergy descriptions are not stored in the Seasonly application database."
        ),
        LegalSection(
            title: "3. Why the information is used",
            body: "Account and profile information is used to provide authentication, seasonal recipe discovery, filtering, favourites, planning, export and deletion. Country and month select the relevant seasonal calendar. Dietary choices filter recipes. Security metadata protects accounts and prevents misuse.\n\nAllergy information is processed only after separate explicit consent so Seasonly can apply conservative exclusions. Recommendation interactions are collected only when separate personalisation consent is active. Agreement to the Terms of Use is not treated as either of these optional consents."
        ),
        LegalSection(
            title: "4. Automated recommendations",
            body: "Seasonly may automatically order eligible recipes using seasonal matches, declared preferences and consented interaction history. Dietary and allergen exclusions are applied before ranking. Recommendations do not make legal or similarly significant decisions about you, and personalisation can be disabled."
        ),
        LegalSection(
            title: "5. Sharing and data sources",
            body: "Seasonly does not sell personal information. Personal account and preference data is not sent to recipe or seasonal-data providers. If hosting or email-delivery providers are configured for private testing, they process only the information needed to operate the service and must follow the project developer’s instructions and applicable data-protection requirements. Recipe and seasonal content comes from documented third-party sources, but those sources do not receive your Seasonly profile."
        ),
        LegalSection(
            title: "6. How long information is kept",
            body: "Account, profile, favourites, history and planning records are kept until you delete the account or the private MVP is discontinued. Identifiable recommendation events expire after no more than 365 days. Security tokens expire or are revoked according to their configured lifetime. Operational access logs, email-provider records and backups may follow separate short retention periods and are not part of the immediate application-database deletion transaction."
        ),
        LegalSection(
            title: "7. Your choices and rights",
            body: "You can edit profile choices, disable personalisation, withdraw allergy-data consent by removing the disclosed allergy profile, download a machine-readable JSON copy of stored information, and permanently delete your account in the app. Depending on applicable law, you may also request access, correction, erasure, restriction, portability or object to processing. Withdrawing consent does not affect processing that was lawful before withdrawal."
        ),
        LegalSection(
            title: "8. Security",
            body: "Seasonly uses password hashing, short-lived access tokens, rotating refresh tokens and iOS Keychain storage. Sensitive export and deletion actions require password reconfirmation. No system can guarantee absolute security, but the MVP is designed to minimise the information collected and restrict access."
        ),
        LegalSection(
            title: "9. Complaints and international use",
            body: "Raise privacy questions with the project developer first. If UK data-protection law applies, you may also complain to the Information Commissioner’s Office at ico.org.uk. The private MVP is designed for local academic testing and does not intentionally arrange international transfers of account data. Any future public hosting must document its processors, locations and transfer safeguards before release."
        ),
        LegalSection(
            title: "10. Changes to this notice",
            body: "The notice version and acknowledgement date are recorded. If Seasonly changes how personal information is used, an updated notice will be shown before the new processing begins. This MVP is for adults aged 18 or over and is not designed for children."
        ),
    ]
}

struct LegalDocumentView: View {
    @Environment(\.dismiss) private var dismiss
    let document: LegalDocument

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Version \(document.version)")
                        Text("Effective \(document.effectiveDate)")
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)

                    Text(document.introduction)
                        .font(.body)
                        .foregroundStyle(SeasonlyColors.ink)

                    ForEach(document.sections) { section in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(section.title)
                                .font(.headline)
                                .foregroundStyle(SeasonlyColors.ink)
                            Text(section.body)
                                .font(.body)
                                .foregroundStyle(SeasonlyColors.ink)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .padding(22)
                .frame(maxWidth: 680, alignment: .leading)
                .frame(maxWidth: .infinity)
            }
            .background(Color(red: 0.94, green: 0.91, blue: 0.83))
            .navigationTitle(document.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

struct CheckboxToggleStyle: ToggleStyle {
    func makeBody(configuration: Configuration) -> some View {
        Button {
            configuration.isOn.toggle()
        } label: {
            HStack(alignment: .top, spacing: 11) {
                Image(systemName: configuration.isOn ? "checkmark.square.fill" : "square")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(configuration.isOn ? SeasonlyColors.brown : .secondary)
                    .accessibilityHidden(true)

                configuration.label
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityValue(configuration.isOn ? "Checked" : "Not checked")
    }
}
