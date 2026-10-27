// Aviso de privacidade: página pública (abre sem login, a partir do rodapé e
// da tela de cadastro).
import { Link } from 'react-router'

import { useAutenticacao } from '../auth/Autenticacao'
import { Logo } from '../componentes/Layout'
import Rodape from '../componentes/Rodape'

const EMAIL = 'o.mathgr@outlook.com'

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg text-esperanca">{titulo}</h2>
      {children}
    </section>
  )
}

export default function Privacidade() {
  const { logado } = useAutenticacao()
  const email = <a href={`mailto:${EMAIL}`} className="text-esperanca underline">{EMAIL}</a>
  return (
    <div className="min-h-screen">
      <header className="border-b border-borda bg-superficie/80">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3">
          <Link to={logado ? '/personagens' : '/entrar'}><Logo /></Link>
          <Link to={logado ? '/personagens' : '/entrar'} className="text-sm text-texto-suave hover:text-texto">
            {logado ? 'Voltar ao app' : 'Entrar'}
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-6 text-sm leading-relaxed">
        <h1 className="text-2xl">Privacidade no Adventurer’s Guide</h1>
        <p>
          O Adventurer’s Guide é um projeto pessoal e gratuito, mantido por Matheus Graciano Ribeiro. Este texto
          explica quais dados o site guarda e por quê.
        </p>

        <Secao titulo="O que guardamos">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <b>Conta:</b> nome, e-mail e senha. A senha nunca é guardada em texto: guardamos apenas uma versão
              protegida (hash Argon2id). Se você entra com o Google, recebemos seu e-mail e um identificador da sua
              conta Google, sem acesso a mais nada.
            </li>
            <li>
              <b>O que você cria:</b> personagens, mesas, sessões, anotações, quadros e as fotos que você enviar.
              Lembre que o que você coloca numa mesa fica visível para os outros membros dela, conforme as
              permissões de jogador e mestre.
            </li>
            <li>
              <b>No seu navegador:</b> o site guarda no armazenamento local o seu acesso e a hora da sua última
              atividade, para manter você conectado e encerrar a sessão depois de 2 horas sem uso. Não usamos
              cookies de propaganda nem ferramentas de rastreamento.
            </li>
          </ul>
        </Secao>

        <Secao titulo="Para que usamos">
          <p>
            Só para o site funcionar: entrar na sua conta, guardar o que você cria e enviar o e-mail de recuperação
            de senha quando você pedir. Não vendemos nem compartilhamos seus dados, e não enviamos propaganda.
          </p>
        </Secao>

        <Secao titulo="Onde ficam">
          <p>
            Num servidor na Oracle Cloud, acessado só por conexão segura (HTTPS). Fazemos uma cópia de segurança por
            dia, e as cópias são mantidas por até 14 dias.
          </p>
        </Secao>

        <Secao titulo="Seus direitos">
          <p>
            Você pode pedir a qualquer momento uma cópia dos seus dados, a correção de algo ou a exclusão da sua
            conta e de tudo o que você criou. Basta escrever para {email}. Depois da exclusão, os dados ainda podem
            existir nas cópias de segurança por até 14 dias, até serem substituídos.
          </p>
        </Secao>

        <Secao titulo="Dúvidas">
          <p>Fale comigo pelo mesmo e-mail.</p>
        </Secao>

        <p className="text-xs text-texto-suave">Última atualização: outubro de 2026.</p>
      </main>
      <Rodape />
    </div>
  )
}
