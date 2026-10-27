// Rodapé de todas as páginas: o aviso de projeto de fã, a atribuição exigida pela
// licença DPCGL (em inglês, como a licença pede) e o link para o aviso de privacidade.
import { Link } from 'react-router'

export default function Rodape() {
  return (
    <footer className="mx-auto max-w-5xl space-y-2 px-4 py-6 text-xs text-texto-suave">
      <p>
        Adventurer’s Guide é um projeto independente de fã, sem afiliação com a Darrington Press ou a Critical Role.
      </p>
      <p lang="en">
        This product includes materials from the Daggerheart System Reference Document 1.0, © Critical Role, LLC.
        under the terms of the Darrington Press Community Gaming (DPCGL) License. More information can be found
        at <a href="https://www.daggerheart.com" target="_blank" rel="noopener noreferrer"
          className="underline hover:text-texto">https://www.daggerheart.com</a>. There are no previous
        modifications by others.
      </p>
      <p><Link to="/privacidade" className="underline hover:text-texto">Aviso de privacidade</Link></p>
    </footer>
  )
}
